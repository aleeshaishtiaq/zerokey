"""Device signals in prepare_training_windows (extension 1.5.3+)."""

from collections import Counter

from src.data_pipeline.prepare_training_windows import device_signals, live_rows

MOUSE = {
    "path_length_px": 500.0,
    "displacement_px": 300.0,
    "average_velocity_px_per_second": 250.0,
    "direction_changes_per_second": 2.0,
    "straightness_ratio": 0.6,
    "click_interval_ms_mean": None,
}


def record(index, **signals):
    return {
        "user_id": "auth0|a",
        "device_id": "d" * 64,
        "session_id": "s1",
        "timestamp": f"2026-11-26T10:00:{index * 15:02d}+00:00",
        "keyboard_features": {},
        "mouse_features": MOUSE | signals,
    }


def test_old_windows_have_no_device_signals():
    assert device_signals(MOUSE) is None


def test_no_scrolling_gives_minus_one_ratio():
    signals = {
        "pointer_event_rate_hz": 118.0,
        "coalesced_events_per_move": 1.8,
        "wheel_event_count": 0,
        "wheel_smooth_ratio": None,
    }
    assert device_signals(MOUSE | signals) == signals | {"wheel_smooth_ratio": -1.0}


def test_signals_written_only_for_new_windows_and_mouse_rows_unchanged():
    records = [
        record(0),
        record(1, pointer_event_rate_hz=79.0, coalesced_events_per_move=1.2,
               wheel_event_count=10, wheel_smooth_ratio=0.9),
    ]
    _, mouse, signals, _ = live_rows(records, Counter())
    assert len(mouse) == 2
    expected = set(MOUSE) - {"click_interval_ms_mean"}
    assert all(set(row["mouse_features"]) == expected for row in mouse)
    assert len(signals) == 1
    assert signals[0]["window_index"] == 1
    assert signals[0]["device_signals"]["wheel_smooth_ratio"] == 0.9
