"""Check feature-table alignment and write user/device mapping files."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .align_live import (
    DEFAULT_LIVE_PATH,
    _read_jsonl,
    _write_jsonl,
    align_records,
)
from .features import (
    BehavioralFeatureSummary,
    KeyboardFeatureSummary,
    MouseFeatureSummary,
)

DEFAULT_UB_PATH = Path("data/processed/features_session0_processed.jsonl")
DEFAULT_LIVE_MAPPING_PATH = Path("data/processed/live_device_mapping.jsonl")
DEFAULT_UB_MAPPING_PATH = Path("data/processed/ub_device_mapping.jsonl")
FEATURE_MODELS = (
    ("keyboard_features", KeyboardFeatureSummary),
    ("mouse_features", MouseFeatureSummary),
)
LIVE_SOURCE_KEYS = {
    "mouse_features.click_interval_ticks_mean": (
        "mouse_features",
        "click_interval_ms_mean",
    ),
}
UB_DEVICE_NAMESPACE = "zerokey-ub-device-mapping-v1"


def _validate_feature_records(
    records: list[dict[str, Any]],
    *,
    source: str,
) -> list[dict[str, Any]]:
    validated = []
    for line_number, record in enumerate(records, start=1):
        try:
            summary = BehavioralFeatureSummary.model_validate(record)
        except ValidationError as error:
            raise ValueError(
                f"{source} line {line_number}: invalid UB feature record: "
                f"{error}"
            ) from error
        validated.append(summary.model_dump(mode="python"))
    if not validated:
        raise ValueError(f"{source} contains no feature records.")
    return validated


def _column_schema() -> list[dict[str, Any]]:
    columns = []
    for group, model in FEATURE_MODELS:
        properties = model.model_json_schema()["properties"]
        for field_name in model.model_fields:
            property_schema = properties[field_name]
            variants = property_schema.get("anyOf", [property_schema])
            value_schema = next(
                variant
                for variant in variants
                if variant.get("type") != "null"
            )
            json_type = value_schema.get("type")
            dtype = {"number": "float64", "integer": "int64"}.get(json_type)
            if dtype is None:
                raise ValueError(
                    f"Unsupported feature type for "
                    f"{group}.{field_name}: {json_type}"
                )
            columns.append(
                {
                    "name": f"{group}.{field_name}",
                    "dtype": dtype,
                    "nullable": any(
                        variant.get("type") == "null" for variant in variants
                    ),
                }
            )
    return columns


def _feature_table(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build ordered feature rows without envelope metadata."""

    columns = _column_schema()
    rows = []
    for record in records:
        row = {}
        for group, model in FEATURE_MODELS:
            features = record[group]
            for field_name in model.model_fields:
                row[f"{group}.{field_name}"] = features[field_name]
        rows.append(row)
    for column in columns:
        for row in rows:
            value = row[column["name"]]
            if value is None:
                if not column["nullable"]:
                    raise ValueError(
                        f"Non-nullable feature {column['name']} contains null."
                    )
                continue
            actual_dtype = (
                "int64"
                if isinstance(value, int) and not isinstance(value, bool)
                else "float64"
                if isinstance(value, float)
                else None
            )
            if actual_dtype != column["dtype"]:
                raise ValueError(
                    f"Feature {column['name']} has dtype {actual_dtype}; "
                    f"expected {column['dtype']}."
                )
    return {"columns": columns, "rows": rows}


def verify_feature_tables(
    df_ub: dict[str, Any],
    df_live: dict[str, Any],
) -> dict[str, Any]:
    """Compare feature names, type/nullability contracts, and column order."""

    ub_columns = df_ub["columns"]
    live_columns = df_live["columns"]
    ub_names = [column["name"] for column in ub_columns]
    live_names = [column["name"] for column in live_columns]
    ub_by_name = {column["name"]: column for column in ub_columns}
    live_by_name = {column["name"]: column for column in live_columns}

    shared_names = set(ub_names) & set(live_names)
    type_differences = [
        {
            "column": name,
            "ub_dtype": ub_by_name[name]["dtype"],
            "live_dtype": live_by_name[name]["dtype"],
        }
        for name in sorted(shared_names)
        if ub_by_name[name]["dtype"] != live_by_name[name]["dtype"]
    ]
    nullability_differences = [
        {
            "column": name,
            "ub_nullable": ub_by_name[name]["nullable"],
            "live_nullable": live_by_name[name]["nullable"],
        }
        for name in sorted(shared_names)
        if ub_by_name[name]["nullable"] != live_by_name[name]["nullable"]
    ]
    ordered_columns_match = ub_names == live_names
    names_match = set(ub_names) == set(live_names)
    schema_matches = (
        names_match
        and ordered_columns_match
        and not type_differences
        and not nullability_differences
        and "device_id" not in ub_names
        and "device_id" not in live_names
    )
    return {
        "schema_matches": schema_matches,
        "ub_feature_count": len(ub_names),
        "live_feature_count": len(live_names),
        "feature_names_match": names_match,
        "column_order_matches": ordered_columns_match,
        "dtypes_match": not type_differences,
        "nullability_matches": not nullability_differences,
        "device_id_excluded": "device_id" not in ub_names + live_names,
        "missing_from_live": sorted(set(ub_names) - set(live_names)),
        "extra_in_live": sorted(set(live_names) - set(ub_names)),
        "type_differences": type_differences,
        "nullability_differences": nullability_differences,
    }


def live_device_mapping(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return unique real user/device pairs from captured live telemetry."""

    pairs = set()
    for line_number, record in enumerate(records, start=1):
        user_id = record.get("user_id")
        device_id = record.get("device_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError(
                f"Live telemetry line {line_number} has no user_id."
            )
        if not isinstance(device_id, str) or not device_id:
            raise ValueError(
                f"Live telemetry line {line_number} has no device_id."
            )
        pairs.add((user_id.strip(), device_id))
    return [
        {"user_id": user_id, "device_id": device_id}
        for user_id, device_id in sorted(pairs)
    ]


def ub_device_mapping(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Create one stable synthetic device ID for each UB user_id."""

    user_ids = set()
    for line_number, record in enumerate(records, start=1):
        user_id = record.get("user_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError(f"UB feature line {line_number} has no user_id.")
        user_ids.add(user_id.strip())
    return [
        {
            "user_id": user_id,
            "device_id": hashlib.sha256(
                f"{UB_DEVICE_NAMESPACE}:{user_id}".encode("utf-8")
            ).hexdigest(),
        }
        for user_id in sorted(user_ids)
    ]


def _live_null_summary(
    df_live: dict[str, Any],
    live_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    report = []
    for column in df_live["columns"]:
        name = column["name"]
        group, feature = name.split(".", 1)
        source_group, source_feature = LIVE_SOURCE_KEYS.get(
            name, (group, feature)
        )
        report.append(
            {
                "feature": name,
                "null_count": sum(
                    row[name] is None for row in df_live["rows"]
                ),
                "missing_in_source_count": sum(
                    source_feature not in record.get(source_group, {})
                    for record in live_records
                ),
            }
        )
    return report


def _rows_with_null_features(df: dict[str, Any]) -> int:
    return sum(
        any(value is None for value in row.values())
        for row in df["rows"]
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report live feature nulls, write device mapping JSONL files, and "
            "verify ordered UB/live feature schemas."
        )
    )
    parser.add_argument("--live-file", type=Path, default=DEFAULT_LIVE_PATH)
    parser.add_argument("--ub-file", type=Path, default=DEFAULT_UB_PATH)
    parser.add_argument(
        "--live-mapping-file", type=Path, default=DEFAULT_LIVE_MAPPING_PATH
    )
    parser.add_argument(
        "--ub-mapping-file", type=Path, default=DEFAULT_UB_MAPPING_PATH
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing mapping files.",
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _build_parser().parse_args(arguments)
    try:
        input_paths = {args.live_file.resolve(), args.ub_file.resolve()}
        output_paths = {
            args.live_mapping_file.resolve(),
            args.ub_mapping_file.resolve(),
        }
        if len(output_paths) != 2 or input_paths & output_paths:
            raise ValueError(
                "Input and mapping output paths must be different."
            )
        if not args.overwrite:
            existing = [path for path in output_paths if path.exists()]
            if existing:
                raise FileExistsError(
                    "Mapping file exists; pass --overwrite to replace it: "
                    + ", ".join(str(path) for path in sorted(existing))
                )

        raw_live_records = _read_jsonl(args.live_file)
        raw_ub_records = _read_jsonl(args.ub_file)
        ub_records = _validate_feature_records(
            raw_ub_records,
            source=str(args.ub_file),
        )
        reserved_subject_ids = {
            int(record["subject_id"]) for record in ub_records
        }
        aligned_live_records = align_records(
            raw_live_records,
            reserved_ub_subject_ids=reserved_subject_ids,
        )
        live_records = _validate_feature_records(
            aligned_live_records,
            source="Aligned live telemetry",
        )

        df_ub = _feature_table(ub_records)
        df_live = _feature_table(live_records)
        schema_report = verify_feature_tables(df_ub, df_live)
        ub_rows_with_nulls = _rows_with_null_features(df_ub)
        live_rows_with_nulls = _rows_with_null_features(df_live)
        null_summary = _live_null_summary(df_live, raw_live_records)
        live_mapping = live_device_mapping(raw_live_records)
        ub_mapping = ub_device_mapping(ub_records)

        _write_jsonl(
            args.live_mapping_file,
            live_mapping,
            overwrite=args.overwrite,
        )
        _write_jsonl(
            args.ub_mapping_file,
            ub_mapping,
            overwrite=args.overwrite,
        )
    except (OSError, ValueError) as error:
        print(f"Device mapping/schema check failed: {error}", file=sys.stderr)
        return 2

    print(
        "Live feature null/missing summary "
        "(nulls are preserved, not imputed):"
    )
    print(
        f"  rows with at least one null feature: "
        f"{live_rows_with_nulls}/{len(df_live['rows'])} "
        f"(all {len(df_live['rows'])} live rows retained)"
    )
    for item in null_summary:
        print(
            f"  {item['feature']}: null={item['null_count']}, "
            f"missing_in_source={item['missing_in_source_count']}"
        )
    print(
        f"\nUB preprocessed rows with at least one null feature: "
        f"{ub_rows_with_nulls}/{len(df_ub['rows'])} "
        "(existing nulls preserved)"
    )
    print("\nFeature schema verification (device_id excluded):")
    result = "MATCH" if schema_report["schema_matches"] else "MISMATCH"
    print(f"  result: {result}")
    print(
        f"  UB/live feature columns: {schema_report['ub_feature_count']}/"
        f"{schema_report['live_feature_count']}"
    )
    print(
        f"  names/order/dtypes/nullability: "
        f"{schema_report['feature_names_match']}/"
        f"{schema_report['column_order_matches']}/"
        f"{schema_report['dtypes_match']}/"
        f"{schema_report['nullability_matches']}"
    )
    if schema_report["missing_from_live"]:
        print(f"  missing from live: {schema_report['missing_from_live']}")
    if schema_report["extra_in_live"]:
        print(f"  extra in live: {schema_report['extra_in_live']}")
    if schema_report["type_differences"]:
        print(f"  dtype differences: {schema_report['type_differences']}")
    if schema_report["nullability_differences"]:
        print(
            "  nullability differences: "
            f"{schema_report['nullability_differences']}"
        )
    print(
        f"\nWrote {len(live_mapping)} live mappings to "
        f"{args.live_mapping_file} "
        f"and {len(ub_mapping)} UB user mappings to {args.ub_mapping_file}."
    )
    return 0 if schema_report["schema_matches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
