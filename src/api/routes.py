import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    field_validator,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from .auth import require_authorized_user
from .settings import resolve_repository_path
from ..data.database import (
    database_configured,
    export_telemetry as db_export_telemetry,
    insert_telemetry,
    list_telemetry,
    telemetry_status,
)

router = APIRouter()
LOGGER = logging.getLogger(__name__)
_default_telemetry_log_path = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "zerokey_captured"
    / "telemetry_log.jsonl"
)
TELEMETRY_LOG_PATH = resolve_repository_path(
    os.getenv("TELEMETRY_LOG_PATH", ""), _default_telemetry_log_path
)
_records_lock = threading.Lock()


def _storage_backend() -> str:
    return "database" if database_configured() else "jsonl"


def _require_writable_storage() -> None:
    if not database_configured() and os.getenv("VERCEL"):
        raise HTTPException(
            status_code=503,
            detail=(
                "DATABASE_URL is not configured on the server. Add it in the "
                "Vercel project's Environment Variables and redeploy."
            ),
        )


class FeatureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MouseFeatures(FeatureModel):
    path_length_px: float = Field(ge=0)
    displacement_px: float = Field(ge=0)
    average_velocity_px_per_second: float = Field(ge=0)
    direction_changes_per_second: float = Field(ge=0)
    straightness_ratio: float | None = Field(default=None, ge=0, le=1)
    click_interval_ms_mean: float | None = Field(default=None, ge=0)
    # Device signals (extension 1.5.3+). Optional so older extensions still work.
    pointer_event_rate_hz: float | None = Field(default=None, ge=0)
    coalesced_events_per_move: float | None = Field(default=None, ge=0)
    wheel_event_count: int | None = Field(default=None, ge=0)
    wheel_smooth_ratio: float | None = Field(default=None, ge=0, le=1)
    # Feature set v2 and mouse v3 (extension 1.6.0+). Optional for older extensions.
    speed_px_per_second_std: float | None = Field(default=None, ge=0)
    speed_px_per_second_median: float | None = Field(default=None, ge=0)
    speed_px_per_second_p90: float | None = Field(default=None, ge=0)
    acceleration_px_per_second2_mean: float | None = Field(default=None, ge=0)
    acceleration_px_per_second2_std: float | None = Field(default=None, ge=0)
    acceleration_px_per_second2_p90: float | None = Field(default=None, ge=0)
    jerk_px_per_second3_mean: float | None = Field(default=None, ge=0)
    jerk_px_per_second3_median: float | None = Field(default=None, ge=0)
    jerk_px_per_second3_p90: float | None = Field(default=None, ge=0)
    right_click_count: int | None = Field(default=None, ge=0)
    stroke_count: int | None = Field(default=None, ge=0)
    stroke_duration_ms_median: float | None = Field(default=None, ge=0)
    stroke_length_px_median: float | None = Field(default=None, ge=0)
    stroke_efficiency_mean: float | None = Field(default=None, ge=0, le=1)
    stroke_efficiency_median: float | None = Field(default=None, ge=0, le=1)
    stroke_deviation_ratio_median: float | None = Field(default=None, ge=0)
    stroke_curvature_rad_per_px_median: float | None = Field(default=None, ge=0)
    stroke_peak_speed_px_per_second_median: float | None = Field(default=None, ge=0)
    stroke_time_to_peak_ratio_median: float | None = Field(default=None, ge=0, le=1)
    stroke_horizontal_share: float | None = Field(default=None, ge=0, le=1)
    click_stroke_share: float | None = Field(default=None, ge=0, le=1)
    pause_before_click_ms_median: float | None = Field(default=None, ge=0)


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
    # Feature set v2 (extension 1.6.0+). Optional for older extensions.
    backspace_rate: float | None = Field(default=None, ge=0, le=1)
    dwell_time_ms_median: float | None = Field(default=None, ge=0)
    pp_latency_ms_median: float | None = Field(default=None, ge=0)
    rp_latency_ms_median: float | None = Field(default=None, ge=0)
    rr_latency_ms_mean: float | None = Field(default=None, ge=0)
    rr_latency_ms_median: float | None = Field(default=None, ge=0)


class TelemetryPayload(FeatureModel):
    collection_version: Literal[2]
    user_id: str | None = None
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
)
def receive_telemetry(
    payload: TelemetryPayload,
    user_id: str = Depends(require_authorized_user),
) -> dict[str, str]:
    record: dict[str, object] = {
        **payload.model_dump(mode="json"),
        "user_id": user_id,
        "timestamp": payload.timestamp.astimezone(timezone.utc).isoformat(),
    }

    _require_writable_storage()
    if database_configured():
        try:
            insert_telemetry(record)
        except (SQLAlchemyError, ValueError) as error:
            LOGGER.exception("Database insert for telemetry failed.")
            raise HTTPException(
                status_code=500,
                detail=f"Unable to save telemetry to the database ({type(error).__name__}).",
            ) from error
    else:
        try:
            TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _records_lock:
                with TELEMETRY_LOG_PATH.open("a", encoding="utf-8") as log_file:
                    line = json.dumps(record, ensure_ascii=False, allow_nan=False)
                    log_file.write(line)
                    log_file.write("\n")
        except OSError as error:
            LOGGER.exception("Writing telemetry to %s failed.", TELEMETRY_LOG_PATH)
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
    if database_configured():
        try:
            records = list_telemetry(limit)
        except (SQLAlchemyError, ValueError) as error:
            LOGGER.exception("Reading recent telemetry from the database failed.")
            raise HTTPException(
                status_code=500,
                detail="Unable to read persisted telemetry records.",
            ) from error
        validated_records = []
        for record in records:
            try:
                validated_records.append(
                    TelemetryPayload.model_validate(record).model_dump(
                        mode="json",
                        exclude_none=False,
                    )
                )
            except ValidationError as error:
                LOGGER.warning("Skipping invalid telemetry row from the database: %s", error)
        return validated_records

    with _records_lock:
        if not TELEMETRY_LOG_PATH.exists():
            return []

        try:
            with TELEMETRY_LOG_PATH.open("r", encoding="utf-8") as log_file:
                recent_records: deque[dict[str, object]] = deque(maxlen=limit)
                for line_number, line in enumerate(log_file, start=1):
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            raise ValueError("Telemetry log entries must be JSON objects.")
                        if record.get("collection_version") != 2:
                            continue
                        validated_record = TelemetryPayload.model_validate(record)
                    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
                        LOGGER.warning(
                            "Skipping invalid telemetry record in %s at line %d: %s",
                            TELEMETRY_LOG_PATH,
                            line_number,
                            error,
                        )
                        continue
                    recent_records.append(
                        validated_record.model_dump(mode="json", exclude_none=False)
                    )
        except OSError as error:
            raise HTTPException(
                status_code=500,
                detail="Unable to read the persisted telemetry records.",
            ) from error

        return list(reversed(recent_records))


@router.get("/telemetry/export")
def export_telemetry(
    _: str = Depends(require_authorized_user),
) -> Response:
    if not database_configured():
        try:
            records = []
            if TELEMETRY_LOG_PATH.exists():
                with TELEMETRY_LOG_PATH.open("r", encoding="utf-8") as log_file:
                    for line in log_file:
                        try:
                            record = json.loads(line)
                            records.append(
                                TelemetryPayload.model_validate(record).model_dump(
                                    mode="json",
                                    exclude_none=False,
                                )
                            )
                        except (json.JSONDecodeError, ValueError, ValidationError):
                            continue
            content = "".join(
                json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
                for record in records
            )
        except OSError as error:
            raise HTTPException(
                status_code=500,
                detail="Unable to export persisted telemetry records.",
            ) from error
        return Response(content=content, media_type="application/x-ndjson")
    try:
        records = db_export_telemetry()
        validated = [
            TelemetryPayload.model_validate(record).model_dump(
                mode="json",
                exclude_none=False,
            )
            for record in records
        ]
        content = "".join(
            json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
            for record in validated
        )
    except (SQLAlchemyError, ValueError, ValidationError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to export persisted telemetry records.",
        ) from error
    return Response(content=content, media_type="application/x-ndjson")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "storage": _storage_backend()}


@router.get("/telemetry/status")
def get_telemetry_status(
    _: str = Depends(require_authorized_user),
) -> dict[str, object]:
    """Show where telemetry is stored and whether it is reachable."""
    status: dict[str, object] = {
        "storage": _storage_backend(),
    }
    if database_configured():
        try:
            status.update(telemetry_status())
            status["database"] = "connected"
        except (SQLAlchemyError, ValueError) as error:
            LOGGER.exception("Telemetry database status check failed.")
            status["database"] = f"error: {type(error).__name__}"
    else:
        status["log_path"] = str(TELEMETRY_LOG_PATH)
        status["log_exists"] = TELEMETRY_LOG_PATH.exists()
    return status


@router.get("/auth/check", dependencies=[Depends(require_authorized_user)])
def check_authorized_access() -> dict[str, str]:
    return {"status": "authorized"}
