import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api import auth
from src.api.main import app
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


def test_extension_telemetry_shape_is_accepted_by_http_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", tmp_path / "telemetry.jsonl")
    monkeypatch.setitem(app.dependency_overrides, auth.require_authorized_user, lambda: "approved")
    payload = make_payload().model_dump(mode="json")

    async def send_payload():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.post("/api/telemetry", json=payload)

    response = asyncio.run(send_payload())
    assert response.status_code == 201, response.text
    assert response.json() == {"status": "accepted"}


def test_recent_telemetry_excludes_legacy_records(tmp_path, monkeypatch):
    log_path = tmp_path / "telemetry.jsonl"
    log_path.write_text(
        json.dumps({"device_id": "legacy-record"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", log_path)

    assert routes.get_recent_telemetry(limit=10) == []


def test_recent_telemetry_skips_malformed_and_schema_invalid_records(tmp_path, monkeypatch):
    log_path = tmp_path / "telemetry.jsonl"
    valid_record = make_payload().model_dump(mode="json")
    log_path.write_text(
        "not json\n"
        + json.dumps({"collection_version": 2, "device_id": "bad"})
        + "\n"
        + json.dumps(valid_record)
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", log_path)

    recent_records = routes.get_recent_telemetry(limit=10)

    assert len(recent_records) == 1
    assert recent_records[0]["session_id"] == valid_record["session_id"]


def test_http_data_routes_fail_closed_until_auth0_allowlist_is_configured(monkeypatch):
    for setting in ("AUTH0_DOMAIN", "AUTH0_AUDIENCE", "AUTH0_ALLOWED_SUBJECTS"):
        monkeypatch.setenv(setting, "")

    async def check_routes():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return (
                await client.get("/api/health"),
                await client.get("/api/auth/check"),
                await client.get("/api/telemetry/recent"),
                await client.post(
                    "/api/telemetry",
                    json=make_payload().model_dump(mode="json"),
                ),
            )

    health, auth_check, recent, submission = asyncio.run(check_routes())
    assert health.status_code == 200
    assert auth_check.status_code == 503
    assert recent.status_code == 503
    assert submission.status_code == 503


def test_authentication_fails_closed_without_an_approved_subject(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.test")
    monkeypatch.delenv("AUTH0_ALLOWED_SUBJECTS", raising=False)

    with pytest.raises(HTTPException) as error:
        auth.require_authorized_user(None)

    assert error.value.status_code == 503


def test_authentication_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.test")
    monkeypatch.setenv("AUTH0_ALLOWED_SUBJECTS", "auth0|approved")

    with pytest.raises(HTTPException) as error:
        auth.require_authorized_user(None)

    assert error.value.status_code == 401


def test_authentication_rejects_unapproved_subject(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.test")
    monkeypatch.setenv("AUTH0_ALLOWED_SUBJECTS", "auth0|approved")
    monkeypatch.setattr(auth, "_jwks_client", lambda _domain: FakeJwksClient())
    monkeypatch.setattr(auth.jwt, "decode", lambda *_args, **_kwargs: {"sub": "auth0|other"})

    with pytest.raises(HTTPException) as error:
        auth.require_authorized_user(bearer_credentials())

    assert error.value.status_code == 403


def test_authentication_accepts_approved_subject_and_checks_jwt_constraints(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.test")
    monkeypatch.setenv("AUTH0_ALLOWED_SUBJECTS", "auth0|approved")
    monkeypatch.setattr(auth, "_jwks_client", lambda _domain: FakeJwksClient())
    decode_options = {}

    def decode(_token, _key, **options):
        decode_options.update(options)
        return {"sub": "auth0|approved"}

    monkeypatch.setattr(auth.jwt, "decode", decode)

    assert auth.require_authorized_user(bearer_credentials()) == "auth0|approved"
    assert decode_options["algorithms"] == ["RS256"]
    assert decode_options["audience"] == "https://api.example.test"
    assert decode_options["issuer"] == "https://example.auth0.com/"
    assert decode_options["options"]["require"] == ["exp", "iat", "iss", "aud", "sub"]


def test_authentication_rejects_invalid_jwt(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", "example.auth0.com")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://api.example.test")
    monkeypatch.setenv("AUTH0_ALLOWED_SUBJECTS", "auth0|approved")
    monkeypatch.setattr(auth, "_jwks_client", lambda _domain: FakeJwksClient())
    monkeypatch.setattr(
        auth.jwt,
        "decode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(auth.jwt.InvalidTokenError()),
    )

    with pytest.raises(HTTPException) as error:
        auth.require_authorized_user(bearer_credentials())

    assert error.value.status_code == 401


def bearer_credentials():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


class FakeJwksClient:
    def get_signing_key_from_jwt(self, _token):
        return type("SigningKey", (), {"key": "test-signing-key"})()
