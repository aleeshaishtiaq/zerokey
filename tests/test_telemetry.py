import json
from uuid import uuid4

from src.api import routes
from src.api.routes import TelemetryPayload


def make_payload() -> TelemetryPayload:
    return TelemetryPayload.model_validate(
        {
            "collection_version": 2,
            "device_id": "a" * 64,
            "session_id": str(uuid4()),
            "timestamp": "2026-10-18T12:00:00+00:00",
            "public_ip_address": None,
            "mouse_features": {
                "path_length_px": 0,
                "displacement_px": 0,
                "average_velocity_px_per_second": 0,
                "direction_changes_per_second": 0,
                "straightness_ratio": None,
                "click_interval_ms_mean": None,
            },
            "keyboard_features": {
                "dwell_time_ms_mean": 100,
                "dwell_time_ms_stddev": 0,
                "pp_latency_ms_mean": None,
                "pp_latency_ms_stddev": None,
                "rp_latency_ms_mean": None,
                "rp_latency_ms_stddev": None,
                "typing_rate_keystrokes_per_minute": 0,
                "pause_count": 0,
                "pause_duration_ms_mean": None,
                "inter_key_interval_ms_stddev": None,
                "rollover_ratio": 0,
            },
        }
    )


def test_receive_telemetry_persists_and_returns_current_record(tmp_path, monkeypatch):
    log_path = tmp_path / "telemetry.jsonl"
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", log_path)
    payload = make_payload()

    assert routes.receive_telemetry(payload) == {"status": "accepted"}

    saved_record = json.loads(log_path.read_text(encoding="utf-8"))
    assert saved_record["collection_version"] == 2
    assert saved_record["public_ip_address"] is None

    recent_records = routes.get_recent_telemetry(limit=10)
    assert len(recent_records) == 1
    assert recent_records[0]["session_id"] == str(payload.session_id)


def test_recent_telemetry_excludes_legacy_records(tmp_path, monkeypatch):
    log_path = tmp_path / "telemetry.jsonl"
    log_path.write_text(
        json.dumps({"device_id": "legacy-record"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", log_path)

    assert routes.get_recent_telemetry(limit=10) == []
