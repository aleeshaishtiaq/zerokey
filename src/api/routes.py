import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
)

from .auth import require_authorized_user

router = APIRouter()
_default_telemetry_log_path = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "zerokey_captured"
    / "telemetry_log.jsonl"
)
TELEMETRY_LOG_PATH = Path(
    os.getenv("TELEMETRY_LOG_PATH", "").strip() or _default_telemetry_log_path
)
_records_lock = threading.Lock()


class FeatureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MouseFeatures(FeatureModel):
    path_length_px: float = Field(ge=0)
    displacement_px: float = Field(ge=0)
    average_velocity_px_per_second: float = Field(ge=0)
    direction_changes_per_second: float = Field(ge=0)
    straightness_ratio: float | None = Field(default=None, ge=0, le=1)
    click_interval_ms_mean: float | None = Field(default=None, ge=0)


class KeyboardFeatures(FeatureModel):
    dwell_time_ms_mean: float | None = Field(default=None, ge=0)
    dwell_time_ms_stddev: float | None = Field(default=None, ge=0)
    pp_latency_ms_mean: float | None = Field(default=None, ge=0)
    pp_latency_ms_stddev: float | None = Field(default=None, ge=0)
    rp_latency_ms_mean: float | None = Field(default=None, ge=0)
    rp_latency_ms_stddev: float | None = Field(default=None, ge=0)
    typing_rate_keystrokes_per_minute: float = Field(ge=0)
    pause_count: int = Field(ge=0)
    pause_duration_ms_mean: float | None = Field(default=None, ge=0)
    inter_key_interval_ms_stddev: float | None = Field(default=None, ge=0)
    rollover_ratio: float = Field(ge=0, le=1)


class TelemetryPayload(FeatureModel):
    collection_version: Literal[2]
    device_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    session_id: UUID
    timestamp: datetime
    public_ip_address: IPvAnyAddress | None = None
    mouse_features: MouseFeatures
    keyboard_features: KeyboardFeatures

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone.")
        return value


@router.post(
    "/telemetry",
    status_code=201,
    dependencies=[Depends(require_authorized_user)],
)
def receive_telemetry(payload: TelemetryPayload) -> dict[str, str]:
    record: dict[str, object] = {
        **payload.model_dump(mode="json"),
        "timestamp": payload.timestamp.astimezone(timezone.utc).isoformat(),
    }

    try:
        TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _records_lock:
            with TELEMETRY_LOG_PATH.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(record, ensure_ascii=False, allow_nan=False))
                log_file.write("\n")
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to persist the telemetry record.",
        ) from error

    return {"status": "accepted"}


@router.get("/telemetry/recent")
def get_recent_telemetry(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    _: str = Depends(require_authorized_user),
) -> list[dict[str, object]]:
    with _records_lock:
        if not TELEMETRY_LOG_PATH.exists():
            return []

        try:
            with TELEMETRY_LOG_PATH.open("r", encoding="utf-8") as log_file:
                recent_records: deque[dict[str, object]] = deque(maxlen=limit)
                for line in log_file:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("Telemetry log entries must be JSON objects.")
                    if record.get("collection_version") == 2:
                        record.setdefault("public_ip_address", None)
                        recent_records.append(record)
        except (OSError, ValueError) as error:
            raise HTTPException(
                status_code=500,
                detail="Unable to read the persisted telemetry records.",
            ) from error

        return list(reversed(recent_records))


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/auth/check", dependencies=[Depends(require_authorized_user)])
def check_authorized_access() -> dict[str, str]:
    return {"status": "authorized"}
