import asyncio

import httpx

from src.api import auth, routes
from src.api.main import app
from tests.test_telemetry import make_payload


def _post(payload, headers=None):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/telemetry", json=payload, headers=headers or {})

    return asyncio.run(send())


def test_extension_reported_ip_is_stored_as_session_ip(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "TELEMETRY_LOG_PATH", tmp_path / "telemetry.jsonl")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setitem(app.dependency_overrides, auth.require_authorized_user, lambda: "approved")
    payload = make_payload().model_dump(mode="json")
    payload["public_ip_address"] = "39.50.10.20"

    assert _post(payload).status_code == 201
    assert routes.get_recent_telemetry(limit=1)[0]["public_ip_address"] == "39.50.10.20"


def test_vercel_without_database_url_returns_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setitem(app.dependency_overrides, auth.require_authorized_user, lambda: "approved")

    response = _post(make_payload().model_dump(mode="json"))

    assert response.status_code == 503
    assert "DATABASE_URL" in response.json()["detail"]


def test_database_recent_returns_newest_first(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'telemetry.db'}")
    monkeypatch.delenv("VERCEL", raising=False)
    for minute in ("00", "01", "02"):
        data = make_payload().model_dump(mode="json")
        data["timestamp"] = f"2026-10-18T12:{minute}:00+00:00"
        routes.receive_telemetry(routes.TelemetryPayload.model_validate(data), user_id="approved")

    recent = routes.get_recent_telemetry(limit=2)

    assert [record["timestamp"][:16] for record in recent] == ["2026-10-18T12:02", "2026-10-18T12:01"]
