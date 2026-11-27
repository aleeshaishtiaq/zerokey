"""Mouse v3 (stroke features) in prepare_training_windows."""

from collections import Counter

import pytest

from src.data_pipeline.prepare_training_windows import (
    STROKE_GAP_MS,
    V3_MOUSE_FEATURES,
    MouseWindow,
    clean_mouse,
    fit_normalization,
    summarize_stroke,
)


def straight_stroke(window, start_x, start_at, steps=5, step_px=20.0, step_ms=10.0):
    for index in range(steps + 1):
        window.move(start_x + index * step_px, 100.0, start_at + index * step_ms)


def test_straight_stroke_shape():
    points = [(index * 20.0, 0.0, index * 10.0) for index in range(6)]
    stroke = summarize_stroke(points)

    assert stroke["length"] == 100
    assert stroke["efficiency"] == 1
    assert stroke["deviation"] == 0
    assert stroke["curvature"] == 0
    assert stroke["peak_speed"] == pytest.approx(2_000)
    assert stroke["horizontal"] is True


def test_short_movements_are_not_strokes():
    assert summarize_stroke([(0, 0, 0), (1, 0, 10), (2, 0, 20)]) is None


def test_pause_splits_strokes_and_click_is_linked():
    window = MouseWindow()
    straight_stroke(window, 0, 0)
    straight_stroke(window, 500, 50 + STROKE_GAP_MS + 1)
    window.click(50 + STROKE_GAP_MS + 1 + 50 + 200)  # 200 ms after the second stroke
    features = window.features()

    assert features["stroke_count"] == 2
    assert features["click_stroke_share"] == 0.5
    assert features["pause_before_click_ms_median"] == 200
    assert features["stroke_horizontal_share"] == 1


def test_window_without_strokes_keeps_row_and_counts_zero():
    window = MouseWindow()
    window.move(0, 0, 0)
    window.move(30, 0, 10)
    report = Counter()
    row, reason = clean_mouse(window.features(), report)

    assert reason == "kept"
    assert row["stroke_count"] == 0
    assert row["stroke_efficiency_median"] == 0
    assert report["mouse_v3_filled_zero_stroke_efficiency_median"] == 1


def test_normalization_includes_v3_when_present():
    base = {"path_length_px": 1.0, "displacement_px": 1.0, "average_velocity_px_per_second": 1.0,
            "direction_changes_per_second": 1.0, "straightness_ratio": 1.0}
    rows = [{"mouse_features": base | {name: 1.0 for name in V3_MOUSE_FEATURES}}]
    assert set(V3_MOUSE_FEATURES) <= set(fit_normalization(rows, "mouse")["features"])
