"""Device-signal mouse features (extension 1.5.3+)."""

import sqlite3

import pytest
from pydantic import ValidationError

from src.api import routes
from src.api.routes import TelemetryPayload
from src.data import database
from tests.test_telemetry import make_payload

SIGNALS = {
    "pointer_event_rate_hz": 118.4,
    "coalesced_events_per_move": 1.79,
    "wheel_event_count": 12,
    "wheel_smooth_ratio": 0.75,
}


def payload_with(**mouse):
    data = make_payload().model_dump(mode="json")
    data["mouse_features"].update(mouse)
    return TelemetryPayload.model_validate(data)


def test_old_extension_payload_without_signals_is_still_accepted():
    payload = make_payload()
    assert payload.mouse_features.pointer_event_rate_hz is None
    assert payload.mouse_features.wheel_smooth_ratio is None


def test_signals_are_validated():
    assert payload_with(**SIGNALS).mouse_features.wheel_event_count == 12
    with pytest.raises(ValidationError):
        payload_with(wheel_smooth_ratio=1.5)
    with pytest.raises(ValidationError):
        payload_with(pointer_event_rate_hz=-1)


def test_signals_are_stored_and_exported(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'telemetry.db'}")
    routes.receive_telemetry(payload_with(**SIGNALS), user_id="auth0|approved")

    exported = database.export_telemetry()[0]["mouse_features"]
    for name, value in SIGNALS.items():
        assert exported[name] == value
    recent = routes.get_recent_telemetry(limit=10)
    assert recent[0]["mouse_features"]["wheel_smooth_ratio"] == 0.75


def test_existing_table_gets_signal_columns_added(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    database_url = f"sqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    routes.receive_telemetry(make_payload(), user_id="auth0|approved")
    with sqlite3.connect(path) as connection:
        for name in SIGNALS:
            connection.execute(f"ALTER TABLE telemetry_records DROP COLUMN {name}")
    monkeypatch.setattr(database, "_initialized_urls", set())

    database.initialize_database(database_url)
    with sqlite3.connect(path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(telemetry_records)")}
    assert set(SIGNALS) <= columns
