"""Build clean, separate keyboard and mouse training windows for UB and live data.

Both sources are turned into 15-second windows using the exact feature
formulas of ``extension/content.js``, so UB and live rows mean the same thing.

Outputs (in ``data/processed/training/``):
    ub_keyboard_windows_clean.jsonl     ub_mouse_windows_clean.jsonl
    live_keyboard_windows_clean.jsonl   live_mouse_windows_clean.jsonl
    data_quality_report.json
    *_windows_normalized.jsonl + normalization_params.json  (see below)

Rules applied identically to UB and live:
    * keyboard and mouse features are stored in separate files;
    * the public IP is never written (it is not a model feature);
    * a window is kept only if it has real activity for that modality;
    * ``pause_duration_ms_mean`` is 0 when ``pause_count`` is 0 (no pauses);
    * features that are almost always undefined are left out (see
      MOUSE_FEATURES / KEYBOARD_FEATURES);
    * any row that still has a null, NaN or infinite value is dropped;
    * exact duplicate live rows are dropped;
    * rows are ordered by subject, session, then window.

UB and live data come from different screens, DPI settings and tasks, so the
same person-independent feature (for example mouse speed) sits on a different
scale in each source. The *_normalized files rescale every feature per source
and per modality with a robust scaler, (value - median) / IQR, fitted on that
source's own windows. After this, a typical window is around 0 in both
sources and UB and live users can be trained and compared together. The
fitted medians/IQRs are saved so new live windows are scaled the same way.

Only the Python standard library is used, so it runs anywhere:
    python -m src.data_pipeline.prepare_training_windows --live-file <export.csv|.jsonl>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

WINDOW_MS = 15_000            # extension WINDOW_DURATION_MS
PAUSE_THRESHOLD_MS = 500      # extension PAUSE_THRESHOLD_MS
MOUSE_GAP_MS = 2_000          # extension burst gap
CLICK_GAP_MS = 2_000          # extension click interval limit
UB_MOUSE_TICKS_PER_MS = 10_000  # .NET DateTime ticks (100 ns)
MIN_KEYDOWNS = 2              # same minimum the live data implies (typing rate needs 2 presses)
MIN_MOUSE_PATH_PX = 1.0       # mouse window must have actually moved

KEYBOARD_FEATURES = [
    "dwell_time_ms_mean",
    "dwell_time_ms_stddev",
    "pp_latency_ms_mean",
    "pp_latency_ms_stddev",
    "rp_latency_ms_mean",
    "rp_latency_ms_stddev",
    "typing_rate_keystrokes_per_minute",
    "pause_count",
    "pause_duration_ms_mean",
    "rollover_ratio",
]
# inter_key_interval_ms_stddev is not used: the extension computes it from the
# same list as pp_latency_ms_stddev, so the two columns are always identical.
# click_interval_ms_mean is left out: it needs two clicks within 2 s inside one
# window, which is rare, so keeping it would delete most mouse rows.
MOUSE_FEATURES = [
    "path_length_px",
    "displacement_px",
    "average_velocity_px_per_second",
    "direction_changes_per_second",
    "straightness_ratio",
]

ROOT = Path(__file__).resolve().parents[2]
UB_KEYSTROKE_ROOT = ROOT / "data/raw/UB_keystroke_dataset"
UB_MOUSE_ROOT = ROOT / "data/raw/UB_mouse_and_events_dataset"
OUTPUT_DIR = ROOT / "data/processed/training"
LIVE_DIR = ROOT / "data/raw/zerokey_captured"


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _std(values: list[float]) -> float | None:
    if not values:
        return None
    average = sum(values) / len(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def ub_device_id(subject_id: str, keyboard_code: int) -> str:
    # Same as parsers.dataset_device_id, so ids match the existing UB files.
    return hashlib.sha256(f"{subject_id}_keyboard{keyboard_code}".encode()).hexdigest()


# --------------------------------------------------------------------------
# Feature collectors: line-by-line ports of extension/content.js
# --------------------------------------------------------------------------
class KeyboardWindow:
    def __init__(self) -> None:
        self.held: dict[str, float] = {}  # survives window flushes, like heldKeys
        self.reset()

    def reset(self) -> None:
        self.key_downs = 0
        self.overlapping = 0
        self.last_down: float | None = None
        self.last_up: float | None = None
        self.active_ms = 0.0
        self.dwell: list[float] = []
        self.rp: list[float] = []
        self.pp: list[float] = []
        self.intervals: list[float] = []
        self.pauses: list[float] = []

    def key_down(self, key: str, at: float) -> None:
        if key in self.held:
            return  # auto-repeat
        if self.held:
            self.overlapping += 1
        self.held[key] = at
        self.key_downs += 1
        if self.last_down is not None:
            interval = at - self.last_down
            if interval >= PAUSE_THRESHOLD_MS:
                self.pauses.append(interval)
            else:
                self.active_ms += interval
                self.intervals.append(interval)
                self.pp.append(interval)
        if self.last_up is not None:
            interval = at - self.last_up
            if 0 <= interval < PAUSE_THRESHOLD_MS:
                self.rp.append(interval)
        self.last_down = at

    def key_up(self, key: str, at: float) -> None:
        pressed = self.held.pop(key, None)
        if pressed is None:
            return
        self.dwell.append(at - pressed)
        self.last_up = at

    def features(self) -> dict[str, Any]:
        return {
            "dwell_time_ms_mean": _mean(self.dwell),
            "dwell_time_ms_stddev": _std(self.dwell),
            "pp_latency_ms_mean": _mean(self.pp),
            "pp_latency_ms_stddev": _std(self.pp),
            "rp_latency_ms_mean": _mean(self.rp),
            "rp_latency_ms_stddev": _std(self.rp),
            "typing_rate_keystrokes_per_minute": (
                self.key_downs / (self.active_ms / 60_000) if self.active_ms > 0 else 0.0
            ),
            "pause_count": len(self.pauses),
            "pause_duration_ms_mean": _mean(self.pauses),
            "inter_key_interval_ms_stddev": _std(self.intervals),
            "rollover_ratio": self.overlapping / self.key_downs if self.key_downs else 0.0,
        }


class MouseWindow:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.previous: tuple[float, float, float] | None = None
        self.burst_start: tuple[float, float, float] | None = None
        self.burst_end: tuple[float, float, float] | None = None
        self.displacement = 0.0
        self.previous_direction: float | None = None
        self.path = 0.0
        self.active_ms = 0.0
        self.direction_changes = 0
        self.moves = 0
        self.clicks = 0
        self.last_click: float | None = None
        self.click_intervals: list[float] = []

    def move(self, x: float, y: float, at: float) -> None:
        point = (x, y, at)
        self.moves += 1
        if self.burst_start is None:
            self.burst_start = point
        if self.previous is not None:
            dx, dy = x - self.previous[0], y - self.previous[1]
            distance = math.hypot(dx, dy)
            elapsed = at - self.previous[2]
            if elapsed > MOUSE_GAP_MS:
                self.displacement += math.hypot(
                    self.burst_end[0] - self.burst_start[0],
                    self.burst_end[1] - self.burst_start[1],
                )
                self.burst_start = point
                self.previous_direction = None
            elif distance > 0 and elapsed > 0:
                self.path += distance
                self.active_ms += elapsed
                direction = math.atan2(dy, dx)
                if self.previous_direction is not None:
                    change = abs(direction - self.previous_direction)
                    if change > math.pi:
                        change = 2 * math.pi - change
                    if change >= math.pi / 4:
                        self.direction_changes += 1
                self.previous_direction = direction
        self.burst_end = point
        self.previous = point

    def click(self, at: float) -> None:
        self.clicks += 1
        if self.last_click is not None and at - self.last_click <= CLICK_GAP_MS:
            self.click_intervals.append(at - self.last_click)
        self.last_click = at

    def features(self) -> dict[str, Any]:
        displacement = self.displacement
        if self.burst_start and self.burst_end:
            displacement += math.hypot(
                self.burst_end[0] - self.burst_start[0],
                self.burst_end[1] - self.burst_start[1],
            )
        seconds = self.active_ms / 1000
        return {
            "path_length_px": self.path,
            "displacement_px": displacement,
            "average_velocity_px_per_second": self.path / seconds if seconds > 0 else 0.0,
            "direction_changes_per_second": (
                self.direction_changes / seconds if seconds > 0 else 0.0
            ),
            "straightness_ratio": min(1.0, displacement / self.path) if self.path > 0 else None,
            "click_interval_ms_mean": _mean(self.click_intervals),
        }


# --------------------------------------------------------------------------
# Cleaning shared by both sources
# --------------------------------------------------------------------------
def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def clean_keyboard(features: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    row = {name: features.get(name) for name in KEYBOARD_FEATURES}
    if row["pause_count"] == 0 and row["pause_duration_ms_mean"] is None:
        row["pause_duration_ms_mean"] = 0.0
    if not _finite(row["typing_rate_keystrokes_per_minute"]) or row["typing_rate_keystrokes_per_minute"] <= 0:
        return None, "no_typing"
    if not all(_finite(value) for value in row.values()):
        return None, "null_or_invalid_feature"
    if any(value < 0 for value in row.values()) or row["rollover_ratio"] > 1:
        return None, "out_of_range"
    row["pause_count"] = int(row["pause_count"])
    return row, "kept"


def clean_mouse(features: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    row = {name: features.get(name) for name in MOUSE_FEATURES}
    if not _finite(row["path_length_px"]) or row["path_length_px"] < MIN_MOUSE_PATH_PX:
        return None, "no_movement"
    if not all(_finite(value) for value in row.values()):
        return None, "null_or_invalid_feature"
    if any(value < 0 for value in row.values()) or row["straightness_ratio"] > 1:
        return None, "out_of_range"
    return row, "kept"


def window_record(
    *, modality: str, source: str, subject_id: str, user_id: str, device_id: str,
    session: int, session_id: str, condition: str, window_index: int,
    window_offset_ms: float, features: dict[str, Any],
) -> dict[str, Any]:
    return {
        "dataset": f"{modality}_feature_window",
        "source": source,
        "subject_id": subject_id,
        "user_id": user_id,
        "device_id": device_id,
        "session": session,
        "session_id": session_id,
        "condition": condition,
        "window_index": window_index,
        "window_offset_ms": round(float(window_offset_ms), 3),
        "window_duration_ms": WINDOW_MS,
        f"{modality}_features": features,
    }


# --------------------------------------------------------------------------
# UB raw files -> windows
# --------------------------------------------------------------------------
UB_NAME = re.compile(r"^(\d{3})([0-2])(\d)(\d)$")


def _ub_meta(stem: str) -> tuple[str, int, int, int] | None:
    match = UB_NAME.match(stem)
    if not match:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4))


def ub_keyboard_rows(report: Counter) -> Iterator[dict[str, Any]]:
    for path in sorted(UB_KEYSTROKE_ROOT.glob("s[0-2]/*/*.txt")):
        meta = _ub_meta(path.stem)
        if meta is None:
            report["ub_keyboard_files_skipped"] += 1
            continue
        subject, session, keyboard_code, _task = meta
        events = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) != 3 or parts[1] not in {"KeyDown", "KeyUp"} or not parts[2].isdigit():
                continue
            events.append((int(parts[2]), parts[1], parts[0]))
        if not events:
            report["ub_keyboard_files_empty"] += 1
            continue
        events.sort(key=lambda event: event[0])
        start = events[0][0]
        collector = KeyboardWindow()
        current = 0
        def flush(index: int) -> Iterator[dict[str, Any]]:
            report["ub_keyboard_windows_total"] += 1
            if collector.key_downs < MIN_KEYDOWNS:
                report["ub_keyboard_dropped_too_few_keys"] += 1
            else:
                row, reason = clean_keyboard(collector.features())
                report[f"ub_keyboard_{reason}"] += 1
                if row:
                    yield window_record(
                        modality="keyboard", source="ub", subject_id=subject, user_id=subject,
                        device_id=ub_device_id(subject, keyboard_code), session=session,
                        session_id=path.stem, condition=path.parent.name,
                        window_index=index, window_offset_ms=index * WINDOW_MS, features=row,
                    )
            collector.reset()
        for at, action, key in events:
            index = int((at - start) // WINDOW_MS)
            if index != current:
                yield from flush(current)
                current = index
            (collector.key_down if action == "KeyDown" else collector.key_up)(key, at)
        yield from flush(current)


def ub_mouse_rows(report: Counter, conditions: dict[str, str]) -> Iterator[dict[str, Any]]:
    for path in sorted(UB_MOUSE_ROOT.glob("*.txt")):
        meta = _ub_meta(path.stem)
        if meta is None:
            report["ub_mouse_files_skipped"] += 1
            continue
        subject, session, keyboard_code, _task = meta
        events = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 4 or not parts[0].isdigit():
                continue
            at = int(parts[0]) / UB_MOUSE_TICKS_PER_MS
            if parts[2] == "Mouse Coordinates":
                try:
                    x, y = (float(value) for value in parts[3].split(","))
                except ValueError:
                    report["ub_mouse_bad_coordinate_lines"] += 1
                    continue
                events.append((at, "move", x, y))
            elif parts[2] == "Left" and parts[3] == "Click":
                events.append((at, "click", 0.0, 0.0))
        if not events:
            report["ub_mouse_files_empty"] += 1
            continue
        events.sort(key=lambda event: event[0])
        start = events[0][0]
        collector = MouseWindow()
        current = 0
        def flush(index: int) -> Iterator[dict[str, Any]]:
            report["ub_mouse_windows_total"] += 1
            row, reason = clean_mouse(collector.features())
            report[f"ub_mouse_{reason}"] += 1
            if row:
                yield window_record(
                    modality="mouse", source="ub", subject_id=subject, user_id=subject,
                    device_id=ub_device_id(subject, keyboard_code), session=session,
                    session_id=path.stem, condition=conditions.get(path.stem, "unknown"),
                    window_index=index, window_offset_ms=index * WINDOW_MS, features=row,
                )
            collector.reset()
        for at, kind, x, y in events:
            index = int((at - start) // WINDOW_MS)
            if index != current:
                yield from flush(current)
                current = index
            if kind == "move":
                collector.move(x, y, at)
            else:
                collector.click(at)
        yield from flush(current)


# --------------------------------------------------------------------------
# Live telemetry (database export) -> separate windows
# --------------------------------------------------------------------------
def _number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if text == "" or text.lower() in {"null", "none", "nan"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_live(path: Path) -> list[dict[str, Any]]:
    """Read a Supabase CSV export, an API NDJSON export or the JSONL fallback."""
    records = []
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                records.append({
                    "user_id": row.get("user_id"),
                    "device_id": row.get("device_id"),
                    "session_id": row.get("session_id"),
                    "timestamp": row.get("timestamp"),
                    "keyboard_features": {k: _number(row.get(k)) for k in KEYBOARD_FEATURES},
                    "mouse_features": {
                        k: _number(row.get(k)) for k in MOUSE_FEATURES + ["click_interval_ms_mean"]
                    },
                })
    else:
        with path.open(encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    records.append(json.loads(line))
    return records


def _parse_time(value: str) -> datetime:
    text = str(value).strip().replace(" ", "T", 1).replace("Z", "+00:00")
    if re.search(r"[+-]\d{2}$", text):
        text += ":00"
    # Postgres drops trailing zeros (".01"); pad to 6 digits for every Python version.
    text = re.sub(r"\.(\d{1,6})(?=[+-]|$)", lambda m: "." + m.group(1).ljust(6, "0"), text)
    return datetime.fromisoformat(text)


def live_rows(records: list[dict[str, Any]], report: Counter):
    usable = []
    seen = set()
    for record in records:
        report["live_records_total"] += 1
        try:
            when = _parse_time(record["timestamp"])
            user = str(record["user_id"]).strip()
            device = str(record["device_id"]).strip()
            session_id = str(record["session_id"]).strip()
        except (KeyError, TypeError, ValueError):
            report["live_records_bad_metadata"] += 1
            continue
        if not user or user == "None" or not session_id:
            report["live_records_bad_metadata"] += 1
            continue
        key = (user, session_id, when.isoformat(),
               json.dumps(record.get("keyboard_features"), sort_keys=True),
               json.dumps(record.get("mouse_features"), sort_keys=True))
        if key in seen:
            report["live_records_duplicate"] += 1
            continue
        seen.add(key)
        usable.append((user, device, session_id, when, record))

    users = sorted({row[0] for row in usable})
    subject_of = {user: f"L{index + 1:02d}" for index, user in enumerate(users)}
    usable.sort(key=lambda row: (subject_of[row[0]], row[3]))

    session_start: dict[tuple[str, str], datetime] = {}
    session_number: dict[tuple[str, str], int] = {}
    per_user_sessions: Counter = Counter()
    window_counter: Counter = Counter()
    keyboard, mouse = [], []
    for user, device, session_id, when, record in usable:
        session_key = (user, session_id)
        if session_key not in session_start:
            session_start[session_key] = when
            session_number[session_key] = per_user_sessions[user]
            per_user_sessions[user] += 1
        index = window_counter[session_key]
        window_counter[session_key] += 1
        common = dict(
            source="live", subject_id=subject_of[user], user_id=user, device_id=device,
            session=session_number[session_key], session_id=session_id, condition="live",
            window_index=index,
            window_offset_ms=(when - session_start[session_key]).total_seconds() * 1000,
        )
        kb_row, kb_reason = clean_keyboard(
            {k: _number(v) for k, v in (record.get("keyboard_features") or {}).items()}
        )
        report[f"live_keyboard_{kb_reason}"] += 1
        if kb_row:
            keyboard.append(window_record(modality="keyboard", features=kb_row, **common))
        ms_row, ms_reason = clean_mouse(
            {k: _number(v) for k, v in (record.get("mouse_features") or {}).items()}
        )
        report[f"live_mouse_{ms_reason}"] += 1
        if ms_row:
            mouse.append(window_record(modality="mouse", features=ms_row, **common))
    order = lambda row: (row["subject_id"], row["session"], row["window_index"])
    keyboard.sort(key=order)
    mouse.sort(key=order)
    return keyboard, mouse, subject_of


# --------------------------------------------------------------------------
def _write(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    temporary = path.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            count += 1
    temporary.replace(path)
    return count


def _quantile(sorted_values: list[float], fraction: float) -> float:
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


def normalize_file(source_path: Path, target_path: Path, modality: str) -> dict[str, Any]:
    """Robust-scale one clean file and return the fitted parameters."""
    rows = [json.loads(line) for line in source_path.open(encoding="utf-8")]
    key = f"{modality}_features"
    names = KEYBOARD_FEATURES if modality == "keyboard" else MOUSE_FEATURES
    params: dict[str, Any] = {"rows_fitted": len(rows), "features": {}}
    for name in names:
        values = sorted(float(row[key][name]) for row in rows)
        median = _quantile(values, 0.5)
        iqr = _quantile(values, 0.75) - _quantile(values, 0.25)
        if iqr <= 0:
            average = sum(values) / len(values)
            iqr = math.sqrt(sum((v - average) ** 2 for v in values) / len(values)) or 1.0
        params["features"][name] = {"median": median, "iqr": iqr}
    for row in rows:
        row[key] = {
            name: (float(row[key][name]) - params["features"][name]["median"])
            / params["features"][name]["iqr"]
            for name in names
        }
        row["dataset"] = f"{modality}_feature_window_normalized"
    _write(target_path, rows)
    return params


def _per_subject(path: Path) -> dict[str, int]:
    counts: Counter = Counter()
    if path.exists():
        with path.open(encoding="utf-8") as source:
            for line in source:
                counts[json.loads(line)["subject_id"]] += 1
    return dict(sorted(counts.items()))


def _latest_live_file() -> Path | None:
    candidates = [
        path for path in LIVE_DIR.glob("*")
        if path.suffix.lower() in {".csv", ".jsonl", ".ndjson"}
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live-file", type=Path, help="Supabase CSV or NDJSON export (default: newest in data/raw/zerokey_captured)")
    parser.add_argument("--skip-ub", action="store_true", help="Only rebuild the live files.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    report: Counter = Counter()
    out = args.output_dir
    summary: dict[str, Any] = {
        "window_ms": WINDOW_MS,
        "keyboard_features": KEYBOARD_FEATURES,
        "mouse_features": MOUSE_FEATURES,
        "min_keydowns_per_ub_window": MIN_KEYDOWNS,
    }

    if not args.skip_ub:
        conditions = {path.stem: path.parent.name for path in UB_KEYSTROKE_ROOT.glob("s[0-2]/*/*.txt")}
        ub_order = lambda row: (row["subject_id"], row["session"], row["session_id"], row["window_index"])
        summary["ub_keyboard_rows"] = _write(
            out / "ub_keyboard_windows_clean.jsonl", sorted(ub_keyboard_rows(report), key=ub_order)
        )
        summary["ub_mouse_rows"] = _write(
            out / "ub_mouse_windows_clean.jsonl", sorted(ub_mouse_rows(report, conditions), key=ub_order)
        )

    live_path = args.live_file or _latest_live_file()
    if live_path is not None:
        keyboard, mouse, subjects = live_rows(read_live(live_path), report)
        summary["live_source_file"] = str(live_path)
        summary["live_subjects"] = subjects
        summary["live_keyboard_rows"] = _write(out / "live_keyboard_windows_clean.jsonl", keyboard)
        summary["live_mouse_rows"] = _write(out / "live_mouse_windows_clean.jsonl", mouse)

    for name in ("ub_keyboard", "ub_mouse", "live_keyboard", "live_mouse"):
        summary[f"{name}_windows_per_subject"] = _per_subject(out / f"{name}_windows_clean.jsonl")
    normalization: dict[str, Any] = {"method": "robust (value - median) / IQR, per source and modality"}
    for name in ("ub_keyboard", "ub_mouse", "live_keyboard", "live_mouse"):
        clean_path = out / f"{name}_windows_clean.jsonl"
        if clean_path.exists() and clean_path.stat().st_size:
            normalization[name] = normalize_file(
                clean_path, out / f"{name}_windows_normalized.jsonl", name.split("_")[1]
            )
    (out / "normalization_params.json").write_text(json.dumps(normalization, indent=2), encoding="utf-8")
    summary["cleaning_counts"] = dict(sorted(report.items()))
    (out / "data_quality_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not k.endswith("per_subject")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
