"""Convert live telemetry windows to the UB feature-summary model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.api.routes import TelemetryPayload
from .features import BehavioralFeatureSummary

DEFAULT_LIVE_PATH = Path("data/raw/zerokey_captured/telemetry_log.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/processed/telemetry_log_ub_aligned.jsonl")
DEFAULT_UB_DIRECTORY = Path("data/processed")
DEFAULT_MOUSE_TICKS_PER_SECOND = 1000.0
HASH_NAMESPACE = "zerokey-live-to-ub-v1"


def _digest(namespace: str, value: str) -> bytes:
    return hashlib.sha256(
        f"{HASH_NAMESPACE}:{namespace}:{value}".encode("utf-8")
    ).digest()


def _hash_index(namespace: str, value: str, size: int) -> int:
    return int.from_bytes(_digest(namespace, value)[:8], "big") % size


def _assign_codes(
    values: set[str],
    *,
    size: int,
    namespace: str,
    reserved: set[int] | None = None,
) -> dict[str, int]:
    """Assign stable hash-started codes, probing to avoid collisions."""

    occupied = set(reserved or ())
    if len(values) + len(occupied) > size:
        raise ValueError(
            f"Cannot map {len(values)} {namespace} identities into {size} available codes."
        )

    assignments: dict[str, int] = {}
    ordered_values = sorted(values, key=lambda value: (_digest(namespace, value), value))
    for value in ordered_values:
        start = _hash_index(namespace, value, size)
        for offset in range(size):
            candidate = (start + offset) % size
            if candidate not in occupied:
                assignments[value] = candidate
                occupied.add(candidate)
                break
        else:
            raise ValueError(f"No unused code remains for {namespace}.")
    return assignments


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required JSONL file does not exist: {path}")
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
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


def _reserved_ub_subject_ids(paths: list[Path]) -> set[int]:
    if not paths:
        raise FileNotFoundError(
            f"No processed UB feature files found under {DEFAULT_UB_DIRECTORY}."
        )
    subject_ids: set[int] = set()
    for path in paths:
        records = _read_jsonl(path)
        for line_number, record in enumerate(records, start=1):
            try:
                summary = BehavioralFeatureSummary.model_validate(record)
            except ValidationError as error:
                raise ValueError(
                    f"{path}:{line_number}: invalid UB feature record: {error}"
                ) from error
            subject_ids.add(int(summary.subject_id))
    return subject_ids


def align_records(
    live_records: list[dict[str, Any]],
    *,
    reserved_ub_subject_ids: set[int],
    mouse_ticks_per_second: float = DEFAULT_MOUSE_TICKS_PER_SECOND,
) -> list[dict[str, Any]]:
    """Return records validated and serialized in the UB feature-summary schema.

    Required UB identifiers are deterministic surrogates, not recovered UB
    experiment labels. Their assignments are stable for a given input batch.
    Nullable feature values remain null; records are not dropped or imputed.
    """

    if not math.isfinite(mouse_ticks_per_second) or mouse_ticks_per_second <= 0:
        raise ValueError("mouse_ticks_per_second must be a finite positive number.")
    if not live_records:
        raise ValueError("Live telemetry JSONL contains no records.")

    payloads: list[tuple[int, TelemetryPayload, str]] = []
    for line_number, record in enumerate(live_records, start=1):
        try:
            payload = TelemetryPayload.model_validate(record)
        except ValidationError as error:
            raise ValueError(
                f"Live telemetry line {line_number} does not match its API model: {error}"
            ) from error
        if payload.user_id is None or not payload.user_id.strip():
            raise ValueError(
                f"Live telemetry line {line_number} has no user_id for subject mapping."
            )
        payloads.append((line_number, payload, payload.user_id.strip()))

    users = {user_id for _, _, user_id in payloads}
    subject_codes = _assign_codes(
        users,
        size=1000,
        namespace="subject_id",
        reserved=reserved_ub_subject_ids,
    )

    session_codes: dict[tuple[str, str], int] = {}
    device_codes: dict[tuple[str, str], int] = {}
    for user_id in users:
        user_payloads = [
            payload for _, payload, record_user_id in payloads if record_user_id == user_id
        ]
        user_sessions = {str(payload.session_id) for payload in user_payloads}
        user_devices = {payload.device_id for payload in user_payloads}
        for session_id, code in _assign_codes(
            user_sessions,
            size=3,
            namespace=f"session:{user_id}",
        ).items():
            session_codes[(user_id, session_id)] = code
        for device_id, code in _assign_codes(
            user_devices,
            size=4,
            namespace=f"keyboard:{user_id}",
        ).items():
            device_codes[(user_id, device_id)] = code

    aligned_records = []
    for line_number, payload, user_id in payloads:
        subject_id = f"{subject_codes[user_id]:03d}"
        session_id = str(payload.session_id)
        session = session_codes[(user_id, session_id)]
        keyboard_code = device_codes[(user_id, payload.device_id)]
        task_id = _hash_index(f"task:{user_id}", session_id, 2)
        subset = (
            "baseline"
            if _hash_index(f"subset:{user_id}", session_id, 2) == 0
            else "rotation"
        )
        original_filename = (
            f"{subject_id}{session}{keyboard_code}{task_id}.txt"
        )

        mouse_features = payload.mouse_features.model_dump(mode="json")
        click_interval_ms = mouse_features.pop("click_interval_ms_mean")
        mouse_features["click_interval_ticks_mean"] = (
            None
            if click_interval_ms is None
            else click_interval_ms * mouse_ticks_per_second / 1000
        )
        aligned = {
            "dataset": "behavioral_feature_window",
            "subject_id": subject_id,
            "user_id": subject_id,
            "device_id": payload.device_id,
            "session": session,
            "keyboard_code": keyboard_code,
            "task_id": task_id,
            "subset": subset,
            "original_filename": original_filename,
            "keyboard_timestamp_unit": "milliseconds",
            "keyboard_ticks_per_second": 1000.0,
            "mouse_timestamp_unit": "milliseconds",
            "mouse_ticks_per_second": mouse_ticks_per_second,
            "keyboard_features": payload.keyboard_features.model_dump(mode="json"),
            "mouse_features": mouse_features,
        }
        try:
            summary = BehavioralFeatureSummary.model_validate(aligned)
        except ValidationError as error:
            raise ValueError(
                f"Converted live telemetry line {line_number} failed UB validation: {error}"
            ) from error
        aligned_records.append(summary.model_dump(mode="json"))
    return aligned_records


def _write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
    *,
    overwrite: bool,
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists; pass --overwrite to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            for record in records:
                destination.write(
                    json.dumps(record, allow_nan=False, sort_keys=True)
                )
                destination.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert live telemetry records to the UB behavioral feature schema. "
            "Generated UB-only identifiers are deterministic surrogates."
        )
    )
    parser.add_argument("--live-file", type=Path, default=DEFAULT_LIVE_PATH)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--ub-file",
        type=Path,
        action="append",
        help="Processed UB feature JSONL to reserve subject IDs; may be repeated.",
    )
    parser.add_argument(
        "--mouse-ticks-per-second",
        type=float,
        default=DEFAULT_MOUSE_TICKS_PER_SECOND,
        help=(
            "Assumed UB mouse ticks per second (default: 1000, a 1:1 "
            "milliseconds-to-ticks mapping)."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output file if it already exists.",
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    if args.output_file.suffix.lower() != ".jsonl":
        print("Output path must have a .jsonl extension.", file=sys.stderr)
        return 2
    try:
        if args.live_file.resolve() == args.output_file.resolve():
            raise ValueError("Input and output paths must be different.")
        ub_paths = args.ub_file
        if ub_paths is None:
            ub_paths = sorted(DEFAULT_UB_DIRECTORY.glob("features_session*_processed.jsonl"))
        reserved_subject_ids = _reserved_ub_subject_ids(ub_paths)
        live_records = _read_jsonl(args.live_file)
        aligned_records = align_records(
            live_records,
            reserved_ub_subject_ids=reserved_subject_ids,
            mouse_ticks_per_second=args.mouse_ticks_per_second,
        )
        _write_jsonl(args.output_file, aligned_records, overwrite=args.overwrite)
    except (OSError, ValueError) as error:
        print(f"Telemetry alignment failed: {error}", file=sys.stderr)
        return 2

    print(f"Aligned {len(aligned_records)} records to {args.output_file}.")
    print(
        "Assumption: UB mouse ticks are 1000 per second; "
        "1 millisecond maps to 1 tick."
    )
    print(
        "UB-only subject/session/device/task/subset identifiers are deterministic "
        "surrogates, not recovered experiment labels."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
