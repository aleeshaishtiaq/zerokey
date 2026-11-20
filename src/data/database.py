import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Identity,
    Integer,
    String,
    Text,
    Uuid,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import TypeDecorator


class InetText(TypeDecorator):
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(INET())
        return dialect.type_descriptor(String(45))


class Base(DeclarativeBase):
    pass


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        Identity(),
        primary_key=True,
    )
    collection_version: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    public_ip_address: Mapped[str | None] = mapped_column(
        InetText(),
        nullable=True,
    )
    path_length_px: Mapped[float] = mapped_column(Float, nullable=False)
    displacement_px: Mapped[float] = mapped_column(Float, nullable=False)
    average_velocity_px_per_second: Mapped[float] = mapped_column(Float, nullable=False)
    direction_changes_per_second: Mapped[float] = mapped_column(Float, nullable=False)
    straightness_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    click_interval_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    dwell_time_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    dwell_time_ms_stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_latency_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_latency_ms_stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    rp_latency_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    rp_latency_ms_stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    typing_rate_keystrokes_per_minute: Mapped[float] = mapped_column(Float, nullable=False)
    pause_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pause_duration_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    inter_key_interval_ms_stddev: Mapped[float | None] = mapped_column(Float, nullable=True)
    rollover_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


_engines: dict[str, Any] = {}


def database_configured(database_url: str | None = None) -> bool:
    url = database_url if database_url is not None else os.getenv("DATABASE_URL", "")
    return bool(url.strip())


def get_database_url(database_url: str | None = None) -> str:
    url = (database_url if database_url is not None else os.getenv("DATABASE_URL", "")).strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine(database_url: str | None = None):
    url = get_database_url(database_url)
    if not url:
        raise ValueError("DATABASE_URL is not configured.")
    engine = _engines.get(url)
    if engine is None:
        engine = create_engine(url, pool_pre_ping=True)
        _engines[url] = engine
    return engine


def initialize_database(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def insert_telemetry(record: dict[str, Any], database_url: str | None = None) -> None:
    initialize_database(database_url)
    mouse = record["mouse_features"]
    keyboard = record["keyboard_features"]
    timestamp = record["timestamp"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    row = TelemetryRecord(
        collection_version=record["collection_version"],
        user_id=record["user_id"],
        device_id=record["device_id"],
        session_id=UUID(str(record["session_id"])),
        timestamp=timestamp,
        public_ip_address=record.get("public_ip_address"),
        path_length_px=mouse["path_length_px"],
        displacement_px=mouse["displacement_px"],
        average_velocity_px_per_second=mouse["average_velocity_px_per_second"],
        direction_changes_per_second=mouse["direction_changes_per_second"],
        straightness_ratio=mouse["straightness_ratio"],
        click_interval_ms_mean=mouse["click_interval_ms_mean"],
        dwell_time_ms_mean=keyboard["dwell_time_ms_mean"],
        dwell_time_ms_stddev=keyboard["dwell_time_ms_stddev"],
        pp_latency_ms_mean=keyboard["pp_latency_ms_mean"],
        pp_latency_ms_stddev=keyboard["pp_latency_ms_stddev"],
        rp_latency_ms_mean=keyboard["rp_latency_ms_mean"],
        rp_latency_ms_stddev=keyboard["rp_latency_ms_stddev"],
        typing_rate_keystrokes_per_minute=keyboard["typing_rate_keystrokes_per_minute"],
        pause_count=keyboard["pause_count"],
        pause_duration_ms_mean=keyboard["pause_duration_ms_mean"],
        inter_key_interval_ms_stddev=keyboard["inter_key_interval_ms_stddev"],
        rollover_ratio=keyboard["rollover_ratio"],
    )
    with Session(get_engine(database_url)) as session:
        session.add(row)
        session.commit()


def list_telemetry(limit: int, database_url: str | None = None) -> list[dict[str, Any]]:
    initialize_database(database_url)
    with Session(get_engine(database_url)) as session:
        rows = session.scalars(
            select(TelemetryRecord)
            .order_by(TelemetryRecord.id.desc())
            .limit(limit)
        ).all()
    return [_serialize(row) for row in reversed(rows)]


def export_telemetry(database_url: str | None = None) -> list[dict[str, Any]]:
    initialize_database(database_url)
    with Session(get_engine(database_url)) as session:
        rows = session.scalars(
            select(TelemetryRecord).order_by(TelemetryRecord.id.asc())
        ).all()
    return [_serialize(row) for row in rows]


def _serialize(row: TelemetryRecord) -> dict[str, Any]:
    timestamp = row.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return {
        "collection_version": row.collection_version,
        "user_id": row.user_id,
        "device_id": row.device_id,
        "session_id": str(row.session_id),
        "timestamp": timestamp.isoformat(),
        "public_ip_address": row.public_ip_address,
        "mouse_features": {
            "path_length_px": row.path_length_px,
            "displacement_px": row.displacement_px,
            "average_velocity_px_per_second": row.average_velocity_px_per_second,
            "direction_changes_per_second": row.direction_changes_per_second,
            "straightness_ratio": row.straightness_ratio,
            "click_interval_ms_mean": row.click_interval_ms_mean,
        },
        "keyboard_features": {
            "dwell_time_ms_mean": row.dwell_time_ms_mean,
            "dwell_time_ms_stddev": row.dwell_time_ms_stddev,
            "pp_latency_ms_mean": row.pp_latency_ms_mean,
            "pp_latency_ms_stddev": row.pp_latency_ms_stddev,
            "rp_latency_ms_mean": row.rp_latency_ms_mean,
            "rp_latency_ms_stddev": row.rp_latency_ms_stddev,
            "typing_rate_keystrokes_per_minute": row.typing_rate_keystrokes_per_minute,
            "pause_count": row.pause_count,
            "pause_duration_ms_mean": row.pause_duration_ms_mean,
            "inter_key_interval_ms_stddev": row.inter_key_interval_ms_stddev,
            "rollover_ratio": row.rollover_ratio,
        },
    }
