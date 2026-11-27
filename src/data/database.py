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
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import NullPool
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
    pointer_event_rate_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    coalesced_events_per_move: Mapped[float | None] = mapped_column(Float, nullable=True)
    wheel_event_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wheel_smooth_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Feature set v2 and mouse v3 (extension 1.6.0+)
    speed_px_per_second_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_px_per_second_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_px_per_second_p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    acceleration_px_per_second2_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    acceleration_px_per_second2_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    acceleration_px_per_second2_p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    jerk_px_per_second3_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    jerk_px_per_second3_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    jerk_px_per_second3_p90: Mapped[float | None] = mapped_column(Float, nullable=True)
    right_click_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stroke_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stroke_duration_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_length_px_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_efficiency_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_efficiency_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_deviation_ratio_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_curvature_rad_per_px_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_peak_speed_px_per_second_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_time_to_peak_ratio_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    stroke_horizontal_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    click_stroke_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    pause_before_click_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    backspace_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    dwell_time_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_latency_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    rp_latency_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr_latency_ms_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr_latency_ms_median: Mapped[float | None] = mapped_column(Float, nullable=True)
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
_initialized_urls: set[str] = set()


def database_configured(database_url: str | None = None) -> bool:
    url = database_url if database_url is not None else os.getenv("DATABASE_URL", "")
    return bool(url.strip())


def get_database_url(database_url: str | None = None) -> str:
    """Normalise DATABASE_URL so any Postgres/Supabase string works as pasted.

    Accepts ``postgres://``, ``postgresql://`` and ``postgresql+psycopg2://``
    URLs, strips surrounding quotes/whitespace, and adds ``sslmode=require``
    for hosted Postgres (Supabase, Neon, ...) when no sslmode is given.
    """
    url = (database_url if database_url is not None else os.getenv("DATABASE_URL", "")).strip()
    if len(url) >= 2 and url[0] == url[-1] and url[0] in {'"', "'"}:
        url = url[1:-1].strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql") and "sslmode=" not in url:
        try:
            host = (make_url(url).host or "").lower()
        except Exception as error:
            raise ValueError(
                "DATABASE_URL could not be parsed. URL-encode special characters "
                "in the password (for example @ -> %40, # -> %23)."
            ) from error
        if host and host not in {"localhost", "127.0.0.1", "::1", "db"}:
            url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def get_engine(database_url: str | None = None):
    url = get_database_url(database_url)
    if not url:
        raise ValueError("DATABASE_URL is not configured.")
    engine = _engines.get(url)
    if engine is None:
        options: dict[str, Any] = {"pool_pre_ping": True}
        if url.startswith("postgresql"):
            options["connect_args"] = {"connect_timeout": 10}
            # Serverless functions (Vercel) are frozen between requests, so a
            # pooled connection is often dead by the next call. Supabase's own
            # pooler already does the pooling for us.
            if os.getenv("VERCEL"):
                options["poolclass"] = NullPool
        engine = create_engine(url, **options)
        _engines[url] = engine
    return engine


def initialize_database(database_url: str | None = None) -> None:
    """Create the table once per process and add any columns that are missing.

    ``create_all`` never alters an existing table, so a table created by an
    older version of this code could be missing newer columns (for example
    ``public_ip_address``) and every insert would fail. This repairs that.
    """
    url = get_database_url(database_url)
    if url in _initialized_urls:
        return
    engine = get_engine(url)
    Base.metadata.create_all(engine)

    table = TelemetryRecord.__table__
    existing = {column["name"] for column in inspect(engine).get_columns(table.name)}
    missing = [column for column in table.columns if column.name not in existing]
    if missing:
        with engine.begin() as connection:
            for column in missing:
                column_type = column.type.compile(dialect=engine.dialect)
                connection.execute(
                    text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}')
                )
    _initialized_urls.add(url)


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
        pointer_event_rate_hz=mouse.get("pointer_event_rate_hz"),
        coalesced_events_per_move=mouse.get("coalesced_events_per_move"),
        wheel_event_count=mouse.get("wheel_event_count"),
        wheel_smooth_ratio=mouse.get("wheel_smooth_ratio"),
        speed_px_per_second_std=mouse.get("speed_px_per_second_std"),
        speed_px_per_second_median=mouse.get("speed_px_per_second_median"),
        speed_px_per_second_p90=mouse.get("speed_px_per_second_p90"),
        acceleration_px_per_second2_mean=mouse.get("acceleration_px_per_second2_mean"),
        acceleration_px_per_second2_std=mouse.get("acceleration_px_per_second2_std"),
        acceleration_px_per_second2_p90=mouse.get("acceleration_px_per_second2_p90"),
        jerk_px_per_second3_mean=mouse.get("jerk_px_per_second3_mean"),
        jerk_px_per_second3_median=mouse.get("jerk_px_per_second3_median"),
        jerk_px_per_second3_p90=mouse.get("jerk_px_per_second3_p90"),
        right_click_count=mouse.get("right_click_count"),
        stroke_count=mouse.get("stroke_count"),
        stroke_duration_ms_median=mouse.get("stroke_duration_ms_median"),
        stroke_length_px_median=mouse.get("stroke_length_px_median"),
        stroke_efficiency_mean=mouse.get("stroke_efficiency_mean"),
        stroke_efficiency_median=mouse.get("stroke_efficiency_median"),
        stroke_deviation_ratio_median=mouse.get("stroke_deviation_ratio_median"),
        stroke_curvature_rad_per_px_median=mouse.get("stroke_curvature_rad_per_px_median"),
        stroke_peak_speed_px_per_second_median=mouse.get("stroke_peak_speed_px_per_second_median"),
        stroke_time_to_peak_ratio_median=mouse.get("stroke_time_to_peak_ratio_median"),
        stroke_horizontal_share=mouse.get("stroke_horizontal_share"),
        click_stroke_share=mouse.get("click_stroke_share"),
        pause_before_click_ms_median=mouse.get("pause_before_click_ms_median"),
        backspace_rate=keyboard.get("backspace_rate"),
        dwell_time_ms_median=keyboard.get("dwell_time_ms_median"),
        pp_latency_ms_median=keyboard.get("pp_latency_ms_median"),
        rp_latency_ms_median=keyboard.get("rp_latency_ms_median"),
        rr_latency_ms_mean=keyboard.get("rr_latency_ms_mean"),
        rr_latency_ms_median=keyboard.get("rr_latency_ms_median"),
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
    # Newest first, matching the JSONL fallback and what the dashboard expects.
    return [_serialize(row) for row in rows]


def telemetry_status(database_url: str | None = None) -> dict[str, Any]:
    initialize_database(database_url)
    with Session(get_engine(database_url)) as session:
        total = session.scalar(select(func.count()).select_from(TelemetryRecord)) or 0
        latest = session.scalar(select(func.max(TelemetryRecord.timestamp)))
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return {
        "record_count": int(total),
        "latest_timestamp": latest.isoformat() if latest else None,
    }


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
            "pointer_event_rate_hz": row.pointer_event_rate_hz,
            "coalesced_events_per_move": row.coalesced_events_per_move,
            "wheel_event_count": row.wheel_event_count,
            "wheel_smooth_ratio": row.wheel_smooth_ratio,
            "speed_px_per_second_std": row.speed_px_per_second_std,
            "speed_px_per_second_median": row.speed_px_per_second_median,
            "speed_px_per_second_p90": row.speed_px_per_second_p90,
            "acceleration_px_per_second2_mean": row.acceleration_px_per_second2_mean,
            "acceleration_px_per_second2_std": row.acceleration_px_per_second2_std,
            "acceleration_px_per_second2_p90": row.acceleration_px_per_second2_p90,
            "jerk_px_per_second3_mean": row.jerk_px_per_second3_mean,
            "jerk_px_per_second3_median": row.jerk_px_per_second3_median,
            "jerk_px_per_second3_p90": row.jerk_px_per_second3_p90,
            "right_click_count": row.right_click_count,
            "stroke_count": row.stroke_count,
            "stroke_duration_ms_median": row.stroke_duration_ms_median,
            "stroke_length_px_median": row.stroke_length_px_median,
            "stroke_efficiency_mean": row.stroke_efficiency_mean,
            "stroke_efficiency_median": row.stroke_efficiency_median,
            "stroke_deviation_ratio_median": row.stroke_deviation_ratio_median,
            "stroke_curvature_rad_per_px_median": row.stroke_curvature_rad_per_px_median,
            "stroke_peak_speed_px_per_second_median": row.stroke_peak_speed_px_per_second_median,
            "stroke_time_to_peak_ratio_median": row.stroke_time_to_peak_ratio_median,
            "stroke_horizontal_share": row.stroke_horizontal_share,
            "click_stroke_share": row.click_stroke_share,
            "pause_before_click_ms_median": row.pause_before_click_ms_median,
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
            "backspace_rate": row.backspace_rate,
            "dwell_time_ms_median": row.dwell_time_ms_median,
            "pp_latency_ms_median": row.pp_latency_ms_median,
            "rp_latency_ms_median": row.rp_latency_ms_median,
            "rr_latency_ms_mean": row.rr_latency_ms_mean,
            "rr_latency_ms_median": row.rr_latency_ms_median,
        },
    }
