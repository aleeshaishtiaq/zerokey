"""Feature set v2 in prepare_training_windows."""

from collections import Counter
from datetime import datetime, timezone

import pytest

from src.data_pipeline.prepare_training_windows import (
    V2_KEYBOARD_FEATURES,
    V2_MOUSE_FEATURES,
    KeyboardWindow,
    MouseWindow,
    clean_keyboard,
    clean_mouse,
    fit_normalization,
    harmonize_v2,
    live_rows,
)


def typed(keys):
    """Press and release each key: down at t, up at t + 100, next key 200 ms later."""
    window = KeyboardWindow()
    for index, key in enumerate(keys):
        start = index * 200.0
        window.key_down(key, start)
        window.key_up(key, start + 100)
    return window


def test_keyboard_v2_values():
    features = typed(["a", "Back", "b", "Backspace"]).features()

    assert features["backspace_rate"] == 0.5
    assert features["dwell_time_ms_median"] == 100
    assert features["pp_latency_ms_median"] == 200
    assert features["rp_latency_ms_median"] == 100
    assert features["rr_latency_ms_mean"] == 200
    assert features["rr_latency_ms_median"] == 200


def test_mouse_v2_speed_acceleration_and_jerk():
    window = MouseWindow()
    # 10 ms steps of 1, 2, 4 and 8 px: speeds 100, 200, 400, 800 px/s
    x = 0.0
    window.move(x, 0, 0)
    for step, at in zip([1, 2, 4, 8], [10, 20, 30, 40]):
        x += step
        window.move(x, 0, at)
    window.right_click()
    features = window.features()

    assert features["speed_px_per_second_median"] == pytest.approx(300)
    assert features["acceleration_px_per_second2_mean"] == pytest.approx((10_000 + 20_000 + 40_000) / 3)
    assert features["jerk_px_per_second3_mean"] == pytest.approx((1_000_000 + 2_000_000) / 2)
    assert features["right_click_count"] == 1


def test_mouse_gap_resets_acceleration():
    window = MouseWindow()
    window.move(0, 0, 0)
    window.move(1, 0, 10)
    window.move(2, 0, 5_000)   # gap: new burst
    window.move(4, 0, 5_010)

    assert window.features()["acceleration_px_per_second2_mean"] is None


def test_v2_is_attached_without_dropping_rows():
    keyboard, reason = clean_keyboard(typed(["a", "b", "c"]).features())
    assert reason == "kept"
    assert set(V2_KEYBOARD_FEATURES) <= set(keyboard)

    window = MouseWindow()
    window.move(0, 0, 0)
    window.move(5, 0, 10)          # one speed sample: no acceleration, no jerk
    report = Counter()
    mouse, reason = clean_mouse(window.features(), report)
    assert reason == "kept"
    assert mouse["jerk_px_per_second3_mean"] == 0.0
    assert report["mouse_v2_filled_zero_jerk_px_per_second3_mean"] == 1


def test_old_rows_without_v2_keep_the_v1_schema():
    old = {name: value for name, value in typed(["a", "b", "c"]).features().items()
           if name not in V2_KEYBOARD_FEATURES}
    row, _ = clean_keyboard(old)
    assert not set(V2_KEYBOARD_FEATURES) & set(row)


def test_mixed_live_versions_drop_v2_and_normalization_follows_the_rows():
    with_v2 = {"mouse_features": {name: 1.0 for name in V2_MOUSE_FEATURES}}
    without = {"mouse_features": {}}
    rows = [with_v2, without]
    report = Counter()
    harmonize_v2(rows, "mouse", V2_MOUSE_FEATURES, report)
    assert rows[0]["mouse_features"] == {}
    assert report["live_mouse_v2_dropped_mixed_versions"] == 1

    base = {"path_length_px": 1.0, "displacement_px": 1.0, "average_velocity_px_per_second": 1.0,
            "direction_changes_per_second": 1.0, "straightness_ratio": 1.0}
    v2_rows = [{"mouse_features": base | {name: 2.0 for name in V2_MOUSE_FEATURES}}]
    assert set(V2_MOUSE_FEATURES) <= set(fit_normalization(v2_rows, "mouse")["features"])
    v1_rows = [{"mouse_features": base}]
    assert not set(V2_MOUSE_FEATURES) & set(fit_normalization(v1_rows, "mouse")["features"])


def test_live_from_ignores_older_windows():
    def record(day):
        return {
            "user_id": "auth0|a", "device_id": "d", "session_id": f"s{day}",
            "timestamp": f"2026-11-{day:02d}T10:00:00+00:00",
            "keyboard_features": {}, "mouse_features": {
                "path_length_px": 10.0, "displacement_px": 5.0,
                "average_velocity_px_per_second": 50.0,
                "direction_changes_per_second": 1.0, "straightness_ratio": 0.5,
            },
        }

    report = Counter()
    _, mouse, _, _ = live_rows([record(26), record(28)], report,
                               live_from=datetime(2026, 11, 27, tzinfo=timezone.utc))
    assert len(mouse) == 1
    assert report["live_records_before_live_from"] == 1
