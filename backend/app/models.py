from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utcnow(): return datetime.now(timezone.utc)

class UTCDateTime(TypeDecorator):
    """Keep timestamps UTC-aware on both PostgreSQL and SQLite."""
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        if dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

class Base(DeclarativeBase): pass

class Society(Base):
    __tablename__ = "societies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    towers: Mapped[list["Tower"]] = relationship(back_populates="society", cascade="all, delete-orphan")
    tanks: Mapped[list["Tank"]] = relationship(back_populates="society", cascade="all, delete-orphan")

class Tower(Base):
    __tablename__ = "towers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    society: Mapped[Society] = relationship(back_populates="towers")
    flats: Mapped[list["Flat"]] = relationship(back_populates="tower", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("society_id", "name"),)

class Flat(Base):
    __tablename__ = "flats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tower_id: Mapped[int] = mapped_column(ForeignKey("towers.id", ondelete="CASCADE"), index=True)
    flat_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    household_type: Mapped[str] = mapped_column(String(40))
    occupant_count: Mapped[int] = mapped_column(Integer)
    tower: Mapped[Tower] = relationship(back_populates="flats")
    meter: Mapped["Meter | None"] = relationship(back_populates="flat", uselist=False, cascade="all, delete-orphan")

class Tank(Base):
    __tablename__ = "tanks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    capacity_litres: Mapped[float] = mapped_column(Float)
    critical_reserve_litres: Mapped[float] = mapped_column(Float)
    society: Mapped[Society] = relationship(back_populates="tanks")

class TankReading(Base):
    __tablename__ = "tank_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tank_id: Mapped[int] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    water_level_litres: Mapped[float] = mapped_column(Float)
    level_percent: Mapped[float] = mapped_column(Float)
    inflow_litres_per_minute: Mapped[float] = mapped_column(Float)
    outflow_litres_per_minute: Mapped[float] = mapped_column(Float)
    pump_state: Mapped[bool] = mapped_column(Boolean)
    __table_args__ = (Index("ix_tank_reading_tank_time", "tank_id", "observed_at"),)

class Meter(Base):
    __tablename__ = "meters"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flat_id: Mapped[int] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), unique=True, index=True)
    serial: Mapped[str] = mapped_column(String(50), unique=True)
    source: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_VIRTUAL_METER")
    flat: Mapped[Flat] = relationship(back_populates="meter")

class MeterReading(Base):
    __tablename__ = "meter_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    consumed_litres: Mapped[float] = mapped_column(Float)
    flow_litres_per_minute: Mapped[float] = mapped_column(Float)
    __table_args__ = (Index("ix_meter_reading_meter_time", "meter_id", "observed_at"),)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(24), index=True)
    flat_id: Mapped[int | None] = mapped_column(ForeignKey("flats.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    level: Mapped[str] = mapped_column(String(20), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)

class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    inputs_json: Mapped[str] = mapped_column(Text)
    results_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class TankerDelivery(Base):
    __tablename__ = "tanker_deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    scheduled_arrival: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    expected_quantity_litres: Mapped[float] = mapped_column(Float)
    actual_quantity_litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="SCHEDULED", index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    comment: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    society_id: Mapped[int] = mapped_column(ForeignKey("societies.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    start_time: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    end_time: Mapped[datetime] = mapped_column(UTCDateTime())
    affected_towers_json: Mapped[str] = mapped_column(Text, default="[]")
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

class AnomalyReview(Base):
    __tablename__ = "anomaly_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flat_id: Mapped[int] = mapped_column(ForeignKey("flats.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24))
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

class AlertRead(Base):
    __tablename__ = "alert_reads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    read_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "alert_id", name="uq_alert_reads_user_alert"),)
