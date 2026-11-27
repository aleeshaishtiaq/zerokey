"""Feature set v2 and mouse v3 fields in the API, the database and the live pipeline."""

import csv
from collections import Counter

import pytest
from pydantic import ValidationError

from src.api import routes
from src.api.routes import TelemetryPayload
from src.data import database
from src.data_pipeline.prepare_training_windows import (
    V2_KEYBOARD_FEATURES,
    V2_MOUSE_FEATURES,
    V3_MOUSE_FEATURES,
    live_rows,
    read_live,
)
from tests.test_telemetry import make_payload

KEYBOARD_V2 = {name: 1.0 for name in V2_KEYBOARD_FEATURES} | {"backspace_rate": 0.1}
MOUSE_NEW = {name: 1.0 for name in V2_MOUSE_FEATURES + V3_MOUSE_FEATURES} | {
    "right_click_count": 2, "stroke_count": 3, "stroke_efficiency_mean": 0.8,
}


def payload_with(mouse=None, keyboard=None):
    data = make_payload().model_dump(mode="json")
    data["mouse_features"].update(mouse or {})
    data["keyboard_features"].update(keyboard or {})
    return TelemetryPayload.model_validate(data)


def test_new_fields_are_optional_and_validated():
    assert make_payload().keyboard_features.backspace_rate is None
    assert payload_with(MOUSE_NEW, KEYBOARD_V2).mouse_features.stroke_count == 3
    with pytest.raises(ValidationError):
        payload_with(keyboard={"backspace_rate": 1.5})
    with pytest.raises(ValidationError):
        payload_with(mouse={"click_stroke_share": -0.1})


def test_new_fields_are_stored_and_exported(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'telemetry.db'}")
    routes.receive_telemetry(payload_with(MOUSE_NEW, KEYBOARD_V2), user_id="auth0|approved")

    exported = database.export_telemetry()[0]
    for name, value in MOUSE_NEW.items():
        assert exported["mouse_features"][name] == value
    for name, value in KEYBOARD_V2.items():
        assert exported["keyboard_features"][name] == value


def test_live_csv_with_new_columns_reaches_the_training_windows(tmp_path):
    keyboard = {
        "dwell_time_ms_mean": 100, "dwell_time_ms_stddev": 10, "pp_latency_ms_mean": 200,
        "pp_latency_ms_stddev": 20, "rp_latency_ms_mean": 100, "rp_latency_ms_stddev": 10,
        "typing_rate_keystrokes_per_minute": 300, "pause_count": 0,
        "pause_duration_ms_mean": None, "rollover_ratio": 0.1,
    } | KEYBOARD_V2
    mouse = {
        "path_length_px": 500, "displacement_px": 300, "average_velocity_px_per_second": 250,
        "direction_changes_per_second": 2, "straightness_ratio": 0.6,
    } | MOUSE_NEW
    row = {"user_id": "auth0|a", "device_id": "d" * 64, "session_id": "s1",
           "timestamp": "2026-11-29T10:00:00+00:00"} | keyboard | mouse
    path = tmp_path / "export.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow({key: "" if value is None else value for key, value in row.items()})

    keyboard_rows, mouse_rows, _, _ = live_rows(read_live(path), Counter())

    assert set(V2_KEYBOARD_FEATURES) <= set(keyboard_rows[0]["keyboard_features"])
    assert set(V2_MOUSE_FEATURES + V3_MOUSE_FEATURES) <= set(mouse_rows[0]["mouse_features"])
