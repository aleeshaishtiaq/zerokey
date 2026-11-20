"""Compare shared UB and live telemetry feature distributions."""

from __future__ import annotations

import argparse
from bisect import bisect_right
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.api.routes import KeyboardFeatures, MouseFeatures, TelemetryPayload
from .features import (
    BehavioralFeatureSummary,
    KeyboardFeatureSummary,
    MouseFeatureSummary,
)

DEFAULT_UB_PATH = Path("data/processed/features_session0_processed.jsonl")
DEFAULT_LIVE_PATH = Path("data/raw/zerokey_captured/telemetry_log.jsonl")

RECORD_MODELS = {
    "ub": BehavioralFeatureSummary,
    "live": TelemetryPayload,
}
FEATURE_MODELS = {
    "keyboard": (KeyboardFeatureSummary, KeyboardFeatures),
    "mouse": (MouseFeatureSummary, MouseFeatures),
}

FEATURES = {
    "mouse.path_length_px": ("mouse", "path_length_px", "path_length_px", False),
    "mouse.displacement_px": ("mouse", "displacement_px", "displacement_px", False),
    "mouse.straightness_ratio": ("mouse", "straightness_ratio", "straightness_ratio", False),
    "mouse.direction_changes_per_second": (
        "mouse",
        "direction_changes_per_second",
        "direction_changes_per_second",
        False,
    ),
    "mouse.click_interval_ms_mean": (
        "mouse",
        "click_interval_ticks_mean",
        "click_interval_ms_mean",
        True,
    ),
    "keyboard.dwell_time_ms_mean": (
        "keyboard",
        "dwell_time_ms_mean",
        "dwell_time_ms_mean",
        False,
    ),
    "keyboard.dwell_time_ms_stddev": (
        "keyboard",
        "dwell_time_ms_stddev",
        "dwell_time_ms_stddev",
        False,
    ),
    "keyboard.pp_latency_ms_mean": (
        "keyboard",
        "pp_latency_ms_mean",
        "pp_latency_ms_mean",
        False,
    ),
    "keyboard.pp_latency_ms_stddev": (
        "keyboard",
        "pp_latency_ms_stddev",
        "pp_latency_ms_stddev",
        False,
    ),
    "keyboard.rp_latency_ms_mean": (
        "keyboard",
        "rp_latency_ms_mean",
        "rp_latency_ms_mean",
        False,
    ),
    "keyboard.rp_latency_ms_stddev": (
        "keyboard",
        "rp_latency_ms_stddev",
        "rp_latency_ms_stddev",
        False,
    ),
    "keyboard.typing_rate_keystrokes_per_minute": (
        "keyboard",
        "typing_rate_keystrokes_per_minute",
        "typing_rate_keystrokes_per_minute",
        False,
    ),
    "keyboard.pause_count": ("keyboard", "pause_count", "pause_count", False),
    "keyboard.pause_duration_ms_mean": (
        "keyboard",
        "pause_duration_ms_mean",
        "pause_duration_ms_mean",
        False,
    ),
    "keyboard.inter_key_interval_ms_stddev": (
        "keyboard",
        "inter_key_interval_ms_stddev",
        "inter_key_interval_ms_stddev",
        False,
    ),
    "keyboard.rollover_ratio": ("keyboard", "rollover_ratio", "rollover_ratio", False),
}


def _nullable_fields(model: type[BaseModel]) -> dict[str, bool]:
    properties = model.model_json_schema()["properties"]
    return {
        name: any(
            option.get("type") == "null"
            for option in properties[name].get("anyOf", [])
        )
        for name in model.model_fields
    }


def _record_key_differences(
    records: list[dict[str, Any]],
    model: type[BaseModel],
) -> list[dict[str, Any]]:
    expected = set(model.model_fields)
    differences = []
    for line_number, record in enumerate(records, start=1):
        actual = set(record)
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            differences.append(
                {
                    "line": line_number,
                    "missing": missing,
                    "unexpected": unexpected,
                }
            )
    return differences


def _feature_key_differences(
    records: list[dict[str, Any]],
    model: type[BaseModel],
) -> list[dict[str, Any]]:
    expected = set(model.model_fields)
    differences = []
    for line_number, record in enumerate(records, start=1):
        actual = set(record)
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing or unexpected:
            differences.append(
                {
                    "line": line_number,
                    "missing": missing,
                    "unexpected": unexpected,
                }
            )
    return differences


def _validation_errors(
    records: list[dict[str, Any]],
    model: type[BaseModel],
) -> list[dict[str, Any]]:
    errors = []
    for line_number, record in enumerate(records, start=1):
        try:
            model.model_validate(record)
        except ValidationError as error:
            errors.append(
                {
                    "line": line_number,
                    "errors": [
                        {
                            "field": ".".join(str(part) for part in item["loc"]),
                            "message": item["msg"],
                            "type": item["type"],
                        }
                        for item in error.errors()
                    ],
                }
            )
    return errors


def _feature_values(
    records: list[dict[str, Any]],
    feature: str,
    *,
    is_ub: bool,
) -> list[float]:
    values = []
    for record in records:
        try:
            value = _value(record, feature, is_ub=is_ub)
        except ValueError:
            continue
        if value is not None:
            values.append(value)
    return values


def verify_schema(
    ub_records: list[dict[str, Any]],
    live_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify exact key and field contracts against the UB and live Pydantic models."""

    records = {"ub": ub_records, "live": live_records}
    envelope_differences = {
        "ub_only": sorted(set(RECORD_MODELS["ub"].model_fields) - set(RECORD_MODELS["live"].model_fields)),
        "live_only": sorted(set(RECORD_MODELS["live"].model_fields) - set(RECORD_MODELS["ub"].model_fields)),
    }
    key_differences: dict[str, dict[str, list[dict[str, Any]]]] = {}
    validation: dict[str, list[dict[str, Any]]] = {}
    for source, model in RECORD_MODELS.items():
        key_differences[source] = {
            "record": _record_key_differences(records[source], model),
            "keyboard_features": [],
            "mouse_features": [],
        }
        validation[source] = _validation_errors(records[source], model)
        for group, (ub_model, live_model) in FEATURE_MODELS.items():
            feature_model = ub_model if source == "ub" else live_model
            nested_records = []
            for record in records[source]:
                nested = record.get(f"{group}_features")
                nested_records.append(nested if isinstance(nested, dict) else {})
            key_differences[source][f"{group}_features"] = _feature_key_differences(
                nested_records,
                feature_model,
            )

    feature_key_schema = {}
    field_contract_differences = []
    for group, (ub_model, live_model) in FEATURE_MODELS.items():
        ub_fields = set(ub_model.model_fields)
        live_fields = set(live_model.model_fields)
        feature_key_schema[group] = {
            "ub_only": sorted(ub_fields - live_fields),
            "live_only": sorted(live_fields - ub_fields),
        }
        ub_nullable = _nullable_fields(ub_model)
        live_nullable = _nullable_fields(live_model)
        for name in sorted(ub_fields & live_fields):
            ub_required = ub_model.model_fields[name].is_required()
            live_required = live_model.model_fields[name].is_required()
            if ub_required != live_required or ub_nullable[name] != live_nullable[name]:
                field_contract_differences.append(
                    {
                        "field": f"{group}_features.{name}",
                        "ub_required": ub_required,
                        "live_required": live_required,
                        "ub_nullable": ub_nullable[name],
                        "live_nullable": live_nullable[name],
                    }
                )

    exact_feature_keys_match = all(
        not difference["ub_only"] and not difference["live_only"]
        for difference in feature_key_schema.values()
    )
    feature_contracts_match = exact_feature_keys_match and not field_contract_differences
    records_validate = all(not errors for errors in validation.values())
    return {
        "schema_matches": (
            feature_contracts_match
            and records_validate
            and not envelope_differences["ub_only"]
            and not envelope_differences["live_only"]
        ),
        "feature_contracts_match": feature_contracts_match,
        "exact_feature_keys_match": exact_feature_keys_match,
        "records_validate_against_own_models": {
            source: not errors for source, errors in validation.items()
        },
        "record_envelope_differences": envelope_differences,
        "feature_key_differences": feature_key_schema,
        "field_contract_differences": field_contract_differences,
        "record_key_differences": key_differences,
        "validation_errors": {
            source: {"count": len(errors), "examples": errors[:10]}
            for source, errors in validation.items()
        },
        "mouse_click_interval": {
            "ub_field": "mouse_features.click_interval_ticks_mean",
            "live_field": "mouse_features.click_interval_ms_mean",
            "ub_timebase": sorted(
                {
                    (
                        record.get("mouse_timestamp_unit"),
                        record.get("mouse_ticks_per_second"),
                    )
                    for record in ub_records
                },
                key=lambda value: (str(value[0]), str(value[1])),
            ),
            "live_unit": "milliseconds (extension uses performance.now())",
            "comparable": False,
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required JSONL file does not exist: {path}")
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object.")
            records.append(record)
    if not records:
        raise ValueError(f"Required JSONL file is empty: {path}")
    return records


def _value(record: dict[str, Any], feature: str, *, is_ub: bool) -> float | None:
    group, ub_key, live_key, needs_unit_conversion = FEATURES[feature]
    nested = record.get(f"{group}_features")
    if not isinstance(nested, dict):
        raise ValueError(f"Record is missing the {group}_features object.")
    value = nested.get(ub_key if is_ub else live_key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Feature {feature} must be a finite number or null.")
    if is_ub and needs_unit_conversion:
        ticks_per_second = record.get("mouse_ticks_per_second", record.get("ticks_per_second"))
        if not isinstance(ticks_per_second, (int, float)) or ticks_per_second <= 0:
            return None
        return float(value) * 1000 / ticks_per_second
    return float(value)


def _ks_statistic(first: list[float], second: list[float]) -> float:
    first_sorted = sorted(first)
    second_sorted = sorted(second)
    candidates = sorted(set(first_sorted + second_sorted))
    return max(
        abs(
            bisect_right(first_sorted, point) / len(first_sorted)
            - bisect_right(second_sorted, point) / len(second_sorted)
        )
        for point in candidates
    )


def compare_records(
    ub_records: list[dict[str, Any]],
    live_records: list[dict[str, Any]],
    *,
    alpha: float = 0.05,
) -> dict[str, Any]:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")
    schema_verification = verify_schema(ub_records, live_records)
    comparisons: list[dict[str, Any]] = []
    incompatible_units: list[str] = []
    for feature in FEATURES:
        ub_values = _feature_values(ub_records, feature, is_ub=True)
        live_values = _feature_values(live_records, feature, is_ub=False)
        if not ub_values:
            if FEATURES[feature][3]:
                incompatible_units.append(feature)
            continue
        if not live_values:
            continue
        comparison: dict[str, Any] = {
            "feature": feature,
            "ub_count": len(ub_values),
            "live_count": len(live_values),
            "ub_mean": statistics.mean(ub_values),
            "live_mean": statistics.mean(live_values),
        }
        if len(ub_values) < 2 or len(live_values) < 2:
            comparison["status"] = "insufficient_samples"
        else:
            statistic = _ks_statistic(ub_values, live_values)
            critical_value = (
                math.sqrt(-0.5 * math.log(alpha / 2))
                * math.sqrt(
                    (len(ub_values) + len(live_values))
                    / (len(ub_values) * len(live_values))
                )
            )
            comparison.update(
                {
                    "ks_statistic": statistic,
                    "ks_critical_value": critical_value,
                    "status": (
                        "insufficient_samples"
                        if critical_value >= 1
                        else "review_difference"
                        if statistic > critical_value
                        else "not_rejected"
                    ),
                }
            )
        comparisons.append(comparison)

    if not live_records:
        status = "blocked_no_live_records"
    elif not comparisons:
        status = "inconclusive_no_comparable_features"
    elif any(item["status"] == "review_difference" for item in comparisons):
        status = "review_distribution_differences"
    elif any(item["status"] == "insufficient_samples" for item in comparisons):
        status = "inconclusive_insufficient_samples"
    else:
        status = "screen_pass"

    return {
        "status": status,
        "alpha": alpha,
        "ub_record_count": len(ub_records),
        "live_record_count": len(live_records),
        "schema": {
            "shared_feature_count": len(comparisons),
            "shared_features": [item["feature"] for item in comparisons],
            "ub_timing_unit_missing": incompatible_units,
            "schema_matches": not incompatible_units and bool(comparisons),
        },
        "schema_verification": schema_verification,
        "distribution_checks": comparisons,
        "interpretation": (
            "A screen pass means the two-sample KS test did not reject equality "
            "at the selected alpha; it does not prove equivalence. UB source-file "
            "summaries and live 15-second windows have different sampling granularity."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sanity-check UB processed features against live telemetry JSONL."
    )
    parser.add_argument("--ub-file", type=Path, default=DEFAULT_UB_PATH)
    parser.add_argument("--live-file", type=Path, default=DEFAULT_LIVE_PATH)
    parser.add_argument("--alpha", type=float, default=0.05)
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    if not 0 < args.alpha < 1:
        print("alpha must be between 0 and 1.", file=sys.stderr)
        return 2
    try:
        report = compare_records(
            _read_jsonl(args.ub_file),
            _read_jsonl(args.live_file),
            alpha=args.alpha,
        )
    except (OSError, ValueError) as error:
        print(f"Sanity check could not run: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 1 if (
        report["status"] == "review_distribution_differences"
        or not report["schema_verification"]["schema_matches"]
    ) else (
        2 if report["status"].startswith("inconclusive") else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
