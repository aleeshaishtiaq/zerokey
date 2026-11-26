"""Cleaning rules in prepare_training_windows."""

from collections import Counter

from src.data_pipeline.prepare_training_windows import (
    MIN_UB_MOUSE_WINDOWS_PER_SUBJECT,
    drop_small_mouse_subjects,
)


def rows(subject, count):
    return [{"subject_id": subject, "window_index": index} for index in range(count)]


def test_small_ub_mouse_subjects_are_dropped():
    data = rows("001", MIN_UB_MOUSE_WINDOWS_PER_SUBJECT) + rows("002", 5)
    report = Counter()

    kept, dropped = drop_small_mouse_subjects(data, report)

    assert dropped == ["002"]
    assert {row["subject_id"] for row in kept} == {"001"}
    assert report["ub_mouse_windows_dropped_small_subject"] == 5


def test_relative_keyboard_features_are_added_and_safe():
    from src.data_pipeline.prepare_training_windows import clean_keyboard

    features = {
        "dwell_time_ms_mean": 100.0,
        "dwell_time_ms_stddev": 20.0,
        "pp_latency_ms_mean": 200.0,
        "pp_latency_ms_stddev": 50.0,
        "rp_latency_ms_mean": 0.0,
        "rp_latency_ms_stddev": 0.0,
        "typing_rate_keystrokes_per_minute": 300.0,
        "pause_count": 0,
        "pause_duration_ms_mean": None,
        "rollover_ratio": 0.1,
    }
    row, reason = clean_keyboard(features)

    assert reason == "kept"
    assert row["dwell_time_cv"] == 0.2
    assert row["pp_latency_cv"] == 0.25
    assert row["rp_latency_cv"] == 0.0  # zero mean does not divide by zero
    assert row["dwell_to_pp_ratio"] == 0.5
    assert row["rp_to_pp_ratio"] == 0.0


def test_ub_splits_are_chronological_by_session():
    from src.data_pipeline.prepare_training_windows import assign_ub_splits

    data = (
        [{"subject_id": "001", "session": 0} for _ in range(4)]
        + [{"subject_id": "001", "session": 1} for _ in range(10)]
        + [{"subject_id": "001", "session": 2} for _ in range(3)]
    )
    splits = [row["split"] for row in assign_ub_splits(data)]

    assert splits[:4] == ["train"] * 4
    assert splits[4:10] == ["train"] * 6          # first 60% of session 1
    assert splits[10:14] == ["calibration"] * 4   # rest of session 1
    assert splits[14:] == ["test"] * 3


def test_live_interim_split_is_60_20_20():
    from src.data_pipeline.prepare_training_windows import assign_live_splits

    data = [{"subject_id": "L01", "split": "round1"} for _ in range(10)]
    splits = [row["split"] for row in assign_live_splits(data)]

    assert splits == ["train"] * 6 + ["calibration"] * 2 + ["test"] * 2


def test_live_round_two_is_test_and_round_one_is_train_and_calibration():
    from src.data_pipeline.prepare_training_windows import assign_live_splits

    data = [{"subject_id": "L01", "split": "round1"} for _ in range(8)]
    data += [{"subject_id": "L01", "split": "test"} for _ in range(3)]
    splits = [row["split"] for row in assign_live_splits(data, has_round2=True)]

    assert splits == ["train"] * 6 + ["calibration"] * 2 + ["test"] * 3
