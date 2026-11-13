"""Behavioral feature engineering for normalized research events."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from statistics import mean, pstdev
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .parsers import NormalizedEvent


class KeyboardFeatureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    dwell_time_ticks_mean: float | None = Field(default=None, ge=0)
    dwell_time_ticks_stddev: float | None = Field(default=None, ge=0)
    press_to_press_ticks_mean: float | None = Field(default=None, ge=0)
    press_to_press_ticks_stddev: float | None = Field(default=None, ge=0)
    release_to_press_ticks_mean: float | None = Field(default=None, ge=0)
    release_to_press_ticks_stddev: float | None = Field(default=None, ge=0)
    typing_rate_keystrokes_per_minute: float | None = Field(default=None, ge=0)
    pause_count: int = Field(ge=0)
    pause_duration_ticks_mean: float | None = Field(default=None, ge=0)
    inter_key_interval_ticks_stddev: float | None = Field(default=None, ge=0)
    rollover_ratio: float | None = Field(default=None, ge=0, le=1)


class MouseFeatureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    path_length_px: float = Field(ge=0)
    displacement_px: float = Field(ge=0)
    average_velocity_px_per_second: float | None = Field(default=None, ge=0)
    direction_changes_per_second: float | None = Field(default=None, ge=0)
    straightness_ratio: float | None = Field(default=None, ge=0, le=1)
    click_interval_ticks_mean: float | None = Field(default=None, ge=0)


class BehavioralFeatureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: str = "behavioral_feature_window"
    subject_id: str
    session: int
    keyboard_code: int
    task_id: int
    subset: str
    original_filename: str
    timestamp_unit: str = "source_ticks"
    ticks_per_second: float | None = Field(default=None, gt=0)
    keyboard_features: KeyboardFeatureSummary
    mouse_features: MouseFeatureSummary


def _summary(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return mean(values), pstdev(values) if len(values) > 1 else 0.0


def _positive_deltas(values: Iterable[int]) -> list[float]:
    ordered = sorted(values)
    return [float(current - previous) for previous, current in zip(ordered, ordered[1:])
            if current > previous]


def extract_keyboard_features(
    records: Iterable[NormalizedEvent],
    *,
    pause_threshold_ticks: int = 500,
    ticks_per_second: float | None = None,
) -> KeyboardFeatureSummary:
    """Summarize keyboard events without converting their source timestamps."""

    ordered = sorted(
        (record for record in records if record.dataset == "keystroke"),
        key=lambda record: (record.timestamp, record.line_number),
    )
    key_downs = [record for record in ordered if record.action == "KeyDown"]
    key_ups = [record for record in ordered if record.action == "KeyUp"]
    down_times = [record.timestamp for record in key_downs]
    up_times = [record.timestamp for record in key_ups]

    press_to_press = _positive_deltas(down_times)
    pause_intervals = [value for value in press_to_press if value >= pause_threshold_ticks]
    active_intervals = [value for value in press_to_press if value < pause_threshold_ticks]
    dwell_by_key: dict[str, deque[int]] = defaultdict(deque)
    dwell_times: list[float] = []
    for record in ordered:
        if record.key is None:
            continue
        if record.action == "KeyDown":
            dwell_by_key[record.key].append(record.timestamp)
        elif record.action == "KeyUp" and dwell_by_key[record.key]:
            pressed_at = dwell_by_key[record.key].popleft()
            if record.timestamp >= pressed_at:
                dwell_times.append(float(record.timestamp - pressed_at))

    last_release: int | None = None
    release_to_press: list[float] = []
    held_keys: set[str] = set()
    rollover_count = 0
    for record in ordered:
        if record.key is None:
            continue
        if record.action == "KeyDown":
            if held_keys:
                rollover_count += 1
            if last_release is not None and record.timestamp >= last_release:
                release_to_press.append(float(record.timestamp - last_release))
            held_keys.add(record.key)
        elif record.action == "KeyUp":
            held_keys.discard(record.key)
            last_release = record.timestamp

    dwell_mean, dwell_stddev = _summary(dwell_times)
    pp_mean, pp_stddev = _summary(press_to_press)
    rp_mean, rp_stddev = _summary(release_to_press)
    pause_mean, _ = _summary(pause_intervals)
    inter_key_stddev = pstdev(active_intervals) if len(active_intervals) > 1 else (
        0.0 if active_intervals else None
    )
    typing_rate = None
    if ticks_per_second and active_intervals:
        active_duration_ticks = sum(active_intervals)
        if active_duration_ticks > 0:
            typing_rate = len(key_downs) / (active_duration_ticks / ticks_per_second) * 60

    return KeyboardFeatureSummary(
        dwell_time_ticks_mean=dwell_mean,
        dwell_time_ticks_stddev=dwell_stddev,
        press_to_press_ticks_mean=pp_mean,
        press_to_press_ticks_stddev=pp_stddev,
        release_to_press_ticks_mean=rp_mean,
        release_to_press_ticks_stddev=rp_stddev,
        typing_rate_keystrokes_per_minute=typing_rate,
        pause_count=len(pause_intervals),
        pause_duration_ticks_mean=pause_mean,
        inter_key_interval_ticks_stddev=inter_key_stddev,
        rollover_ratio=rollover_count / len(key_downs) if key_downs else None,
    )


def extract_mouse_features(
    records: Iterable[NormalizedEvent],
    *,
    ticks_per_second: float | None = None,
) -> MouseFeatureSummary:
    """Summarize coordinate and explicitly parsed click events."""

    ordered = sorted(
        (record for record in records if record.dataset == "mouse"),
        key=lambda record: (record.timestamp, record.line_number),
    )
    coordinates = [
        record for record in ordered
        if record.event_type == "mouse_move" and record.x is not None and record.y is not None
    ]
    path_length = 0.0
    direction_changes = 0
    previous_angle: float | None = None
    active_duration_ticks = 0
    for previous, current in zip(coordinates, coordinates[1:]):
        elapsed = current.timestamp - previous.timestamp
        if elapsed <= 0:
            continue
        dx = current.x - previous.x
        dy = current.y - previous.y
        distance = math.hypot(dx, dy)
        active_duration_ticks += elapsed
        path_length += distance
        if distance == 0:
            continue
        angle = math.atan2(dy, dx)
        if previous_angle is not None:
            angle_change = abs(angle - previous_angle)
            if angle_change > math.pi:
                angle_change = 2 * math.pi - angle_change
            if angle_change >= math.pi / 4:
                direction_changes += 1
        previous_angle = angle

    displacement = 0.0
    if len(coordinates) >= 2:
        displacement = math.hypot(
            coordinates[-1].x - coordinates[0].x,
            coordinates[-1].y - coordinates[0].y,
        )
    click_times = [record.timestamp for record in ordered if record.event_type == "mouse_click"]
    click_intervals = _positive_deltas(click_times)
    velocity = None
    direction_rate = None
    if ticks_per_second and active_duration_ticks > 0:
        seconds = active_duration_ticks / ticks_per_second
        velocity = path_length / seconds
        direction_rate = direction_changes / seconds

    return MouseFeatureSummary(
        path_length_px=path_length,
        displacement_px=displacement,
        average_velocity_px_per_second=velocity,
        direction_changes_per_second=direction_rate,
        straightness_ratio=displacement / path_length if path_length > 0 else None,
        click_interval_ticks_mean=mean(click_intervals) if click_intervals else None,
    )


def build_feature_summary(
    records: Iterable[NormalizedEvent],
    *,
    ticks_per_second: float | None = None,
    pause_threshold_ticks: int = 500,
) -> BehavioralFeatureSummary:
    """Build one aligned keyboard/mouse feature record for one source file."""

    grouped = list(records)
    if not grouped:
        raise ValueError("Cannot build features from an empty event group.")
    reference = next(
        (record.keystroke_reference for record in grouped if record.keystroke_reference),
        None,
    )
    first = grouped[0]
    if reference is None:
        if first.keyboard_code is None or first.task_id is None:
            raise ValueError("Feature group lacks documented keystroke metadata.")
        subject_id = first.subject_id
        session = first.session
        keyboard_code = first.keyboard_code
        task_id = first.task_id
        subset = first.condition
    else:
        subject_id = reference.subject_id
        session = reference.session
        keyboard_code = reference.keyboard_code
        task_id = reference.task_id
        subset = reference.subset
    return BehavioralFeatureSummary(
        subject_id=subject_id,
        session=session,
        keyboard_code=keyboard_code,
        task_id=task_id,
        subset=subset,
        original_filename=first.original_filename,
        ticks_per_second=ticks_per_second,
        keyboard_features=extract_keyboard_features(
            grouped,
            pause_threshold_ticks=pause_threshold_ticks,
            ticks_per_second=ticks_per_second,
        ),
        mouse_features=extract_mouse_features(grouped, ticks_per_second=ticks_per_second),
    )