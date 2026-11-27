"""Load training windows from data/processed/training/ and group them per user."""

import json
from pathlib import Path

import numpy as np

DEFAULT_DATA_DIR = Path("data") / "processed" / "training"
SPLITS = ("train", "calibration", "test")

ABSOLUTE_KEYBOARD_FEATURES = (
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
)
RELATIVE_KEYBOARD_FEATURES = (
    "dwell_time_cv",
    "pp_latency_cv",
    "rp_latency_cv",
    "dwell_to_pp_ratio",
    "rp_to_pp_ratio",
)
# Feature set v2 (zip v5 onwards, UB only for now; live gets them with a new
# extension version).
KEYBOARD_V2_FEATURES = (
    "backspace_rate",
    "dwell_time_ms_median",
    "pp_latency_ms_median",
    "rp_latency_ms_median",
    "rr_latency_ms_mean",
    "rr_latency_ms_median",
)
KEYBOARD_FEATURE_SETS = {
    "abs10": ABSOLUTE_KEYBOARD_FEATURES,
    "all15": ABSOLUTE_KEYBOARD_FEATURES + RELATIVE_KEYBOARD_FEATURES,
    "abs10_v2": ABSOLUTE_KEYBOARD_FEATURES + KEYBOARD_V2_FEATURES,
    "all21": ABSOLUTE_KEYBOARD_FEATURES + RELATIVE_KEYBOARD_FEATURES + KEYBOARD_V2_FEATURES,
}
MOUSE_FEATURES = (
    "path_length_px",
    "displacement_px",
    "average_velocity_px_per_second",
    "direction_changes_per_second",
    "straightness_ratio",
)
MOUSE_V2_FEATURES = (
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
)
MOUSE_FEATURE_SETS = {
    "mouse5": MOUSE_FEATURES,
    "mouse15": MOUSE_FEATURES + MOUSE_V2_FEATURES,
}
FEATURE_SETS = {"keyboard": KEYBOARD_FEATURE_SETS, "mouse": MOUSE_FEATURE_SETS}


def window_file(data_dir, source, modality, split, kind="clean"):
    return Path(data_dir) / f"{source}_{modality}_{split}_{kind}.jsonl"


def read_windows(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def to_matrix(windows, features, feature_key="keyboard_features"):
    """Return (X, user_ids) with columns in the order of ``features``."""
    matrix = np.array(
        [[float(window[feature_key][name]) for name in features] for window in windows],
        dtype=float,
    )
    users = np.array([str(window["user_id"]) for window in windows])
    if matrix.size and not np.isfinite(matrix).all():
        raise ValueError("training windows contain NaN or infinite values")
    return matrix.reshape(len(windows), len(features)), users


def load_split(data_dir, source, modality, split, features, kind="clean"):
    windows = read_windows(window_file(data_dir, source, modality, split, kind))
    return to_matrix(windows, features, f"{modality}_features")
