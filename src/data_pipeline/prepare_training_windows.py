"""Build clean, separate keyboard and mouse training windows for UB and live data.

Both sources are turned into 15-second windows using the exact feature
formulas of ``extension/content.js``, so UB and live rows mean the same thing.

Outputs (in ``data/processed/training/``), for each source (ub, live),
modality (keyboard, mouse) and split (train, calibration, test):
    <source>_<modality>_<split>_clean.jsonl
    <source>_<modality>_<split>_normalized.jsonl
plus live_mouse_device_signals.jsonl (extension 1.5.3+ only, see below),
normalization_params.json and data_quality_report.json.

Splits (chronological, so no future behaviour leaks into training):
    UB    train = session 0 + first 60% of session 1, calibration = rest of
          session 1, test = session 2 (recorded weeks later).
    live  split inside every session, in time order, so every session (for
          example a touchpad-only session) also reaches train. With
          --live-test-from (a later collection round, after a gap): earlier
          sessions = 75% train / 25% calibration each, later round = test.
          Without it (interim, until round 2 exists): each session 60% train
          / 20% calibration / 20% test.
Train is for fitting the models, calibration for thresholds and risk-state
boundaries, test only for the final metrics.

Rules applied identically to UB and live:
    * keyboard and mouse features are stored in separate files;
    * the public IP is never written (it is not a model feature);
    * a window is kept only if it has real activity for that modality;
    * ``pause_duration_ms_mean`` is 0 when ``pause_count`` is 0 (no pauses);
    * features that are almost always undefined are left out (see
      MOUSE_FEATURES / KEYBOARD_FEATURES);
    * any row that still has a null, NaN or infinite value is dropped;
    * exact duplicate live rows are dropped;
    * UB subjects with fewer than MIN_UB_MOUSE_WINDOWS_PER_SUBJECT mouse
      windows are left out of the mouse files (their keyboard windows stay);
    * rows are ordered by subject, session, then window.

UB and live data come from different screens, DPI settings and tasks, so the
same person-independent feature (for example mouse speed) sits on a different
scale in each source. The *_normalized files rescale every feature per source
and per modality with a robust scaler, (value - median) / IQR, fitted on that
source's own **train** windows and then applied to every split, so calibration
and test data never influence it. After this, a typical window is around 0 in
both sources. The fitted medians/IQRs are saved so new live windows are scaled
the same way.

Relative timing features (RELATIVE_KEYBOARD_FEATURES) are added to every
keyboard window, UB and live alike. They are ratios of the absolute timings
(spread / mean, and dwell or release-press time relative to press-press time),
so they change less when a whole session gets faster or slower, for example on
a different keyboard. Absolute features are kept, so training can compare
"absolute only" with "absolute + relative".

Feature set v2 (V2_KEYBOARD_FEATURES, V2_MOUSE_FEATURES) is added next to
all earlier features; nothing is removed and no window is dropped because of
it. Keyboard: backspace rate (a count only), median dwell / press-press /
release-press, release-release mean and median. Mouse: speed std / median /
p90, acceleration mean / std / p90, jerk mean / median / p90 (from
consecutive movement samples inside a burst) and right-click count. A v2
value that cannot be computed in a window is set to 0 and counted in the
report. Live rows sent before the v2 extension have no v2 values; a live file
only carries v2 when every window has it (see --live-from).

Device signals (pointer event rate, coalesced events per move, wheel event
count, share of smooth wheel events) are raw input characteristics sent by
extension 1.5.3+. They help training split one user's pointer data into
profiles (touchpad, mouse, ...) without labelling the device. UB data and
older live rows do not have them, so they are written to their own file,
keyed by subject_id + session_id + window_index, and the clean files keep
the same structure for UB and live.

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
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

WINDOW_MS = 15_000            # extension WINDOW_DURATION_MS
PAUSE_THRESHOLD_MS = 500      # extension PAUSE_THRESHOLD_MS
MOUSE_GAP_MS = 2_000          # extension burst gap
CLICK_GAP_MS = 2_000          # extension click interval limit
UB_MOUSE_TICKS_PER_MS = 10_000  # .NET DateTime ticks (100 ns)
MIN_KEYDOWNS = 2              # same minimum the live data implies (typing rate needs 2 presses)
MIN_MOUSE_PATH_PX = 1.0       # mouse window must have actually moved
# A UB subject needs this many mouse windows (all sessions together) for a
# usable per-user mouse model; fewer leave only a handful of test windows.
MIN_UB_MOUSE_WINDOWS_PER_SUBJECT = 60
SPLITS = ("train", "calibration", "test")
UB_SESSION1_TRAIN_FRACTION = 0.6   # rest of UB session 1 = calibration
LIVE_SPLIT_INTERIM = (0.6, 0.2)    # no round 2 yet: train, calibration (rest = test)
LIVE_SPLIT_WITH_ROUND2 = (0.75, 0.25)  # round 1 = train + calibration only
PAKISTAN_TIME = timezone(timedelta(hours=5))

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
# Feature set v2: added next to the features above (nothing removed). The
# extension computes the same values with the same formulas.
V2_KEYBOARD_FEATURES = [
    "backspace_rate",          # backspace key-downs / all key-downs (a count, no key text)
    "dwell_time_ms_median",
    "pp_latency_ms_median",
    "rp_latency_ms_median",
    "rr_latency_ms_mean",      # release-release, consecutive releases < PAUSE_THRESHOLD_MS
    "rr_latency_ms_median",
]
V2_MOUSE_FEATURES = [
    "speed_px_per_second_std",
    "speed_px_per_second_median",
    "speed_px_per_second_p90",
    "acceleration_px_per_second2_mean",
    "acceleration_px_per_second2_std",
    "acceleration_px_per_second2_p90",
    "jerk_px_per_second3_mean",
    "jerk_px_per_second3_median",
    "jerk_px_per_second3_p90",
    "right_click_count",
]
BACKSPACE_KEYS = {"Back", "Backspace"}  # UB virtual-key name, browser KeyboardEvent.key
# Derived from the features above (see relative_keyboard_features).
RELATIVE_KEYBOARD_FEATURES = [
    "dwell_time_cv",
    "pp_latency_cv",
    "rp_latency_cv",
    "dwell_to_pp_ratio",
    "rp_to_pp_ratio",
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
# Live only (extension 1.5.3+); written to live_mouse_device_signals.jsonl.
DEVICE_SIGNAL_FEATURES = [
    "pointer_event_rate_hz",
    "coalesced_events_per_move",
    "wheel_event_count",
    "wheel_smooth_ratio",
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


def _median(values: list[float]) -> float | None:
    return _quantile(sorted(values), 0.5) if values else None


def _p90(values: list[float]) -> float | None:
    return _quantile(sorted(values), 0.9) if values else None


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
        self.backspaces = 0
        self.rr: list[float] = []

    def key_down(self, key: str, at: float) -> None:
        if key in self.held:
            return  # auto-repeat
        if self.held:
            self.overlapping += 1
        self.held[key] = at
        self.key_downs += 1
        if key in BACKSPACE_KEYS:
            self.backspaces += 1
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
        if self.last_up is not None:
            interval = at - self.last_up
            if 0 <= interval < PAUSE_THRESHOLD_MS:
                self.rr.append(interval)
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
            "backspace_rate": self.backspaces / self.key_downs if self.key_downs else 0.0,
            "dwell_time_ms_median": _median(self.dwell),
            "pp_latency_ms_median": _median(self.pp),
            "rp_latency_ms_median": _median(self.rp),
            "rr_latency_ms_mean": _mean(self.rr),
            "rr_latency_ms_median": _median(self.rr),
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
        self.right_clicks = 0
        self.speeds: list[float] = []
        self.accelerations: list[float] = []
        self.jerks: list[float] = []
        self.last_speed: float | None = None
        self.last_acceleration: float | None = None

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
                self.last_speed = None
                self.last_acceleration = None
            elif distance > 0 and elapsed > 0:
                self.path += distance
                self.active_ms += elapsed
                self._kinematics(distance, elapsed)
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

    def _kinematics(self, distance: float, elapsed: float) -> None:
        """Speed, then |change| of speed and of acceleration, per second."""
        seconds = elapsed / 1000
        speed = distance / seconds
        self.speeds.append(speed)
        if self.last_speed is not None:
            acceleration = abs(speed - self.last_speed) / seconds
            self.accelerations.append(acceleration)
            if self.last_acceleration is not None:
                self.jerks.append(abs(acceleration - self.last_acceleration) / seconds)
            self.last_acceleration = acceleration
        self.last_speed = speed

    def right_click(self) -> None:
        self.right_clicks += 1

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
            "speed_px_per_second_std": _std(self.speeds),
            "speed_px_per_second_median": _median(self.speeds),
            "speed_px_per_second_p90": _p90(self.speeds),
            "acceleration_px_per_second2_mean": _mean(self.accelerations),
            "acceleration_px_per_second2_std": _std(self.accelerations),
            "acceleration_px_per_second2_p90": _p90(self.accelerations),
            "jerk_px_per_second3_mean": _mean(self.jerks),
            "jerk_px_per_second3_median": _median(self.jerks),
            "jerk_px_per_second3_p90": _p90(self.jerks),
            "right_click_count": self.right_clicks,
        }


# --------------------------------------------------------------------------
# Cleaning shared by both sources
# --------------------------------------------------------------------------
def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def attach_v2(row: dict[str, Any], features: dict[str, Any], names: list[str],
              report: Counter | None, modality: str) -> None:
    """Add feature set v2 to a kept row, without ever dropping the row.

    Older live rows have no v2 values at all; they keep the v1 schema. A value
    that cannot be computed in one window (for example jerk needs three
    movement samples) is set to 0.0 and counted in the report.
    """
    if not all(name in features for name in names):
        return
    for name in names:
        value = features[name]
        if not _finite(value) or value < 0:
            value = 0.0
            if report is not None:
                report[f"{modality}_v2_filled_zero_{name}"] += 1
        row[name] = float(value)


def clean_keyboard(features: dict[str, Any],
                   report: Counter | None = None) -> tuple[dict[str, Any] | None, str]:
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
    row.update(relative_keyboard_features(row))
    attach_v2(row, features, V2_KEYBOARD_FEATURES, report, "keyboard")
    return row, "kept"


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 0.0


def relative_keyboard_features(row: dict[str, Any]) -> dict[str, float]:
    """Timing ratios that are less sensitive to overall speed or keyboard model."""
    return {
        "dwell_time_cv": _ratio(row["dwell_time_ms_stddev"], row["dwell_time_ms_mean"]),
        "pp_latency_cv": _ratio(row["pp_latency_ms_stddev"], row["pp_latency_ms_mean"]),
        "rp_latency_cv": _ratio(row["rp_latency_ms_stddev"], row["rp_latency_ms_mean"]),
        "dwell_to_pp_ratio": _ratio(row["dwell_time_ms_mean"], row["pp_latency_ms_mean"]),
        "rp_to_pp_ratio": _ratio(row["rp_latency_ms_mean"], row["pp_latency_ms_mean"]),
    }


def clean_mouse(features: dict[str, Any],
                report: Counter | None = None) -> tuple[dict[str, Any] | None, str]:
    row = {name: features.get(name) for name in MOUSE_FEATURES}
    if not _finite(row["path_length_px"]) or row["path_length_px"] < MIN_MOUSE_PATH_PX:
        return None, "no_movement"
    if not all(_finite(value) for value in row.values()):
        return None, "null_or_invalid_feature"
    if any(value < 0 for value in row.values()) or row["straightness_ratio"] > 1:
        return None, "out_of_range"
    attach_v2(row, features, V2_MOUSE_FEATURES, report, "mouse")
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
                row, reason = clean_keyboard(collector.features(), report)
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
            elif parts[2] == "Right" and parts[3] == "Click":
                events.append((at, "right_click", 0.0, 0.0))
        if not events:
            report["ub_mouse_files_empty"] += 1
            continue
        events.sort(key=lambda event: event[0])
        start = events[0][0]
        collector = MouseWindow()
        current = 0

        def flush(index: int) -> Iterator[dict[str, Any]]:
            report["ub_mouse_windows_total"] += 1
            row, reason = clean_mouse(collector.features(), report)
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
            elif kind == "right_click":
                collector.right_click()
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
            reader = csv.DictReader(source)
            columns = set(reader.fieldnames or [])
            keyboard_names = KEYBOARD_FEATURES + [n for n in V2_KEYBOARD_FEATURES if n in columns]
            mouse_names = (
                MOUSE_FEATURES + ["click_interval_ms_mean"] + DEVICE_SIGNAL_FEATURES
                + [n for n in V2_MOUSE_FEATURES if n in columns]
            )
            for row in reader:
                records.append({
                    "user_id": row.get("user_id"),
                    "device_id": row.get("device_id"),
                    "session_id": row.get("session_id"),
                    "timestamp": row.get("timestamp"),
                    "keyboard_features": {k: _number(row.get(k)) for k in keyboard_names},
                    "mouse_features": {k: _number(row.get(k)) for k in mouse_names},
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


def _live_order(row: dict[str, Any]) -> tuple:
    return row["subject_id"], row["session"], row["window_index"]


def _ub_order(row: dict[str, Any]) -> tuple:
    return row["subject_id"], row["session"], row["session_id"], row["window_index"]


def live_rows(records: list[dict[str, Any]], report: Counter,
              test_from: datetime | None = None, live_from: datetime | None = None):
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
        if live_from is not None and when < live_from:
            report["live_records_before_live_from"] += 1
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
    keyboard, mouse, signals = [], [], []
    for user, device, session_id, when, record in usable:
        split = "test" if test_from is not None and when >= test_from else "round1"
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
            {k: _number(v) for k, v in (record.get("keyboard_features") or {}).items()}, report
        )
        report[f"live_keyboard_{kb_reason}"] += 1
        if kb_row:
            keyboard.append(window_record(modality="keyboard", features=kb_row, **common)
                            | {"split": split})
        mouse_values = {k: _number(v) for k, v in (record.get("mouse_features") or {}).items()}
        ms_row, ms_reason = clean_mouse(mouse_values, report)
        report[f"live_mouse_{ms_reason}"] += 1
        if ms_row:
            mouse.append(window_record(modality="mouse", features=ms_row, **common)
                         | {"split": split})
            signal_row = device_signals(mouse_values)
            report[f"live_device_signals_{'kept' if signal_row else 'missing'}"] += 1
            if signal_row:
                signals.append({
                    key: common[key]
                    for key in ("source", "subject_id", "user_id", "device_id",
                                "session", "session_id", "window_index")
                } | {"split": split, "device_signals": signal_row})
    keyboard.sort(key=_live_order)
    mouse.sort(key=_live_order)
    harmonize_v2(keyboard, "keyboard", V2_KEYBOARD_FEATURES, report)
    harmonize_v2(mouse, "mouse", V2_MOUSE_FEATURES, report)
    assign_live_splits(keyboard, has_round2=test_from is not None)
    assign_live_splits(mouse, has_round2=test_from is not None)
    mouse_split = {(r["subject_id"], r["session_id"], r["window_index"]): r["split"] for r in mouse}
    for row in signals:
        row["split"] = mouse_split[(row["subject_id"], row["session_id"], row["window_index"])]
    signals.sort(key=_live_order)
    return keyboard, mouse, signals, subject_of


def harmonize_v2(rows: list[dict[str, Any]], modality: str, names: list[str],
                 report: Counter) -> None:
    """Keep one schema per file: v2 only if every window has it.

    Live rows sent before the v2 extension have no v2 values. If old and new
    rows are mixed, v2 is removed from all of them (use --live-from to keep
    only the new rows instead).
    """
    key = f"{modality}_features"
    with_v2 = sum(1 for row in rows if names[0] in row[key])
    report[f"live_{modality}_windows_with_v2"] += with_v2
    if 0 < with_v2 < len(rows):
        report[f"live_{modality}_v2_dropped_mixed_versions"] += with_v2
        for row in rows:
            for name in names:
                row[key].pop(name, None)


def assign_live_splits(rows: list[dict[str, Any]], has_round2: bool = False) -> list[dict[str, Any]]:
    """Live split inside each session, in time order.

    With a later round (rows already marked "test"): each round-1 session =
    75% train / 25% calibration. Without one: each session 60% train / 20%
    calibration / 20% test. ``rows`` must be in _live_order (time order).
    """
    train_fraction, calibration_fraction = (
        LIVE_SPLIT_WITH_ROUND2 if has_round2 else LIVE_SPLIT_INTERIM
    )
    round1: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["split"] == "round1":
            round1[(row["subject_id"], row["session_id"])].append(row)
    for subject_rows in round1.values():
        train_end = math.ceil(len(subject_rows) * train_fraction)
        calibration_end = math.ceil(len(subject_rows) * (train_fraction + calibration_fraction))
        for index, row in enumerate(subject_rows):
            if index < train_end:
                row["split"] = "train"
            elif index < calibration_end:
                row["split"] = "calibration"
            else:
                row["split"] = "test"
    return rows


def assign_ub_splits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """UB: session 0 + first part of session 1 = train, rest of 1 = calibration, 2 = test.

    ``rows`` must already be in _ub_order, so "first part" means earliest windows.
    """
    session1: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["session"] == 0:
            row["split"] = "train"
        elif row["session"] == 2:
            row["split"] = "test"
        else:
            session1[row["subject_id"]].append(row)
    for subject_rows in session1.values():
        cut = math.ceil(len(subject_rows) * UB_SESSION1_TRAIN_FRACTION)
        for index, row in enumerate(subject_rows):
            row["split"] = "train" if index < cut else "calibration"
    return rows


def device_signals(mouse_values: dict[str, Any]) -> dict[str, Any] | None:
    """Device signals of one mouse window, or None for windows sent before 1.5.3.

    The wheel ratio is undefined when nobody scrolled; it is set to -1 then,
    so every row is complete and "no scrolling" stays distinguishable.
    """
    rate = mouse_values.get("pointer_event_rate_hz")
    per_move = mouse_values.get("coalesced_events_per_move")
    if not (_finite(rate) and _finite(per_move)) or rate <= 0 or per_move <= 0:
        return None
    wheel_count = mouse_values.get("wheel_event_count")
    wheel_count = int(wheel_count) if _finite(wheel_count) and wheel_count >= 0 else 0
    smooth = mouse_values.get("wheel_smooth_ratio")
    smooth = float(smooth) if wheel_count > 0 and _finite(smooth) and 0 <= smooth <= 1 else -1.0
    return {
        "pointer_event_rate_hz": float(rate),
        "coalesced_events_per_move": float(per_move),
        "wheel_event_count": wheel_count,
        "wheel_smooth_ratio": smooth,
    }


def drop_small_mouse_subjects(
    rows: list[dict[str, Any]], report: Counter
) -> tuple[list[dict[str, Any]], list[str]]:
    """Remove UB subjects whose mouse data is too small for a per-user model."""
    counts = Counter(row["subject_id"] for row in rows)
    small = sorted(subject for subject, count in counts.items()
                   if count < MIN_UB_MOUSE_WINDOWS_PER_SUBJECT)
    report["ub_mouse_windows_dropped_small_subject"] += sum(counts[s] for s in small)
    return [row for row in rows if row["subject_id"] not in small], small


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


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def _feature_names(modality: str, rows: list[dict[str, Any]] | None = None) -> list[str]:
    """Features to scale; v2 is included when the rows carry it."""
    if modality == "keyboard":
        names, v2 = KEYBOARD_FEATURES + RELATIVE_KEYBOARD_FEATURES, V2_KEYBOARD_FEATURES
    else:
        names, v2 = list(MOUSE_FEATURES), V2_MOUSE_FEATURES
    if rows and all(v2[0] in row[f"{modality}_features"] for row in rows):
        names = names + v2
    return names


def fit_normalization(rows: list[dict[str, Any]], modality: str) -> dict[str, Any]:
    """Robust (median / IQR) scaler fitted on the given (train) rows."""
    key = f"{modality}_features"
    params: dict[str, Any] = {"rows_fitted": len(rows), "fitted_on": "train", "features": {}}
    for name in _feature_names(modality, rows):
        values = sorted(float(row[key][name]) for row in rows)
        median = _quantile(values, 0.5)
        iqr = _quantile(values, 0.75) - _quantile(values, 0.25)
        if iqr <= 0:
            average = sum(values) / len(values)
            iqr = math.sqrt(sum((v - average) ** 2 for v in values) / len(values)) or 1.0
        params["features"][name] = {"median": median, "iqr": iqr}
    return params


def apply_normalization(
    rows: list[dict[str, Any]], modality: str, params: dict[str, Any]
) -> list[dict[str, Any]]:
    key = f"{modality}_features"
    scaled = []
    for row in rows:
        row = dict(row)
        row[key] = {
            name: (float(row[key][name]) - params["features"][name]["median"])
            / params["features"][name]["iqr"]
            for name in params["features"]
        }
        row["dataset"] = f"{modality}_feature_window_normalized"
        scaled.append(row)
    return scaled


def _write_splits(out: Path, name: str, rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        split: _write(out / f"{name}_{split}_clean.jsonl", [r for r in rows if r["split"] == split])
        for split in SPLITS
    }


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
    parser.add_argument(
        "--live-test-from",
        help="Date (YYYY-MM-DD, Pakistan time) when a later live collection "
             "round started; all live windows from then on go to the test split.",
    )
    parser.add_argument(
        "--live-from",
        help="Date (YYYY-MM-DD, Pakistan time): ignore live windows before it, for "
             "example to use only data from a newer extension version.",
    )
    args = parser.parse_args(argv)
    live_from = None
    if args.live_from:
        live_from = datetime.fromisoformat(args.live_from)
        if live_from.tzinfo is None:
            live_from = live_from.replace(tzinfo=PAKISTAN_TIME)
    test_from = None
    if args.live_test_from:
        test_from = datetime.fromisoformat(args.live_test_from)
        if test_from.tzinfo is None:
            test_from = test_from.replace(tzinfo=PAKISTAN_TIME)

    report: Counter = Counter()
    out = args.output_dir
    summary: dict[str, Any] = {
        "window_ms": WINDOW_MS,
        "keyboard_features": KEYBOARD_FEATURES,
        "keyboard_relative_features": RELATIVE_KEYBOARD_FEATURES,
        "keyboard_v2_features": V2_KEYBOARD_FEATURES,
        "mouse_v2_features": V2_MOUSE_FEATURES,
        "mouse_features": MOUSE_FEATURES,
        "min_keydowns_per_ub_window": MIN_KEYDOWNS,
        "min_ub_mouse_windows_per_subject": MIN_UB_MOUSE_WINDOWS_PER_SUBJECT,
        "splits": {
            "ub": "train = session 0 + first 60% of session 1; calibration = rest of "
                  "session 1; test = session 2",
            "live": "inside every session, time order: with --live-test-from 75% train "
                    "/ 25% calibration and the later round = test; without it 60/20/20",
            "live_test_from": test_from.isoformat() if test_from else None,
            "live_from": live_from.isoformat() if live_from else None,
        },
    }

    if not args.skip_ub:
        conditions = {path.stem: path.parent.name for path in UB_KEYSTROKE_ROOT.glob("s[0-2]/*/*.txt")}
        summary["ub_keyboard_rows"] = _write_splits(
            out, "ub_keyboard", assign_ub_splits(sorted(ub_keyboard_rows(report), key=_ub_order))
        )
        ub_mouse, small_subjects = drop_small_mouse_subjects(
            list(ub_mouse_rows(report, conditions)), report
        )
        summary["ub_mouse_subjects_dropped_too_few_windows"] = small_subjects
        summary["ub_mouse_rows"] = _write_splits(
            out, "ub_mouse", assign_ub_splits(sorted(ub_mouse, key=_ub_order))
        )

    live_path = args.live_file or _latest_live_file()
    if live_path is not None:
        keyboard, mouse, signals, subjects = live_rows(read_live(live_path), report, test_from, live_from)
        summary["live_source_file"] = str(live_path)
        summary["live_subjects"] = subjects
        summary["live_keyboard_rows"] = _write_splits(out, "live_keyboard", keyboard)
        summary["live_mouse_rows"] = _write_splits(out, "live_mouse", mouse)
        summary["live_device_signal_rows"] = _write(out / "live_mouse_device_signals.jsonl", signals)

    normalization: dict[str, Any] = {
        "method": "robust (value - median) / IQR, per source and modality, fitted on train only"
    }
    for name in ("ub_keyboard", "ub_mouse", "live_keyboard", "live_mouse"):
        modality = name.split("_")[1]
        summary[f"{name}_windows_per_subject"] = {
            split: _per_subject(out / f"{name}_{split}_clean.jsonl") for split in SPLITS
        }
        train = _read(out / f"{name}_train_clean.jsonl")
        if not train:
            continue
        params = fit_normalization(train, modality)
        normalization[name] = params
        for split in SPLITS:
            rows = train if split == "train" else _read(out / f"{name}_{split}_clean.jsonl")
            _write(out / f"{name}_{split}_normalized.jsonl",
                   apply_normalization(rows, modality, params))
    (out / "normalization_params.json").write_text(json.dumps(normalization, indent=2), encoding="utf-8")
    summary["cleaning_counts"] = dict(sorted(report.items()))
    (out / "data_quality_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if not k.endswith("per_subject")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
