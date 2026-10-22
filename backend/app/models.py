from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Computed,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(300))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(20), default="participant")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Token(Base):
    __tablename__ = "tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    expires: Mapped[datetime] = mapped_column(DateTime)


class Import(Base):
    __tablename__ = "luma_imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    actor: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Attendee(Base):
    __tablename__ = "luma_attendees"
    id: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[str] = mapped_column(String(200), unique=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    approval: Mapped[str] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("luma_imports.id"))
    raw: Mapped[dict] = mapped_column(JSON)
    normalized: Mapped[dict] = mapped_column(JSON)


class Profile(Base):
    __tablename__ = "participant_profiles"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    availability_override: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Window(Base):
    __tablename__ = "matching_windows"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    active_slot: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "CASE WHEN status IN ('scheduled','open','closing','matching','review','failed') THEN 1 ELSE NULL END"
        ),
        unique=True,
    )
    opens: Mapped[datetime] = mapped_column(DateTime)
    closes: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    policy: Mapped[dict] = mapped_column(JSON)
    config: Mapped[dict] = mapped_column(JSON)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (CheckConstraint("closes > opens"),)


class Registration(Base):
    __tablename__ = "registrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    window_id: Mapped[int] = mapped_column(ForeignKey("matching_windows.id"))
    state: Mapped[str] = mapped_column(String(30), default="joined")
    eligibility: Mapped[dict] = mapped_column(JSON, default=dict)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "window_id"),)


class Snapshot(Base):
    __tablename__ = "dataset_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    window_id: Mapped[int] = mapped_column(
        ForeignKey("matching_windows.id"), unique=True
    )
    import_id: Mapped[int | None] = mapped_column(ForeignKey("luma_imports.id"))
    pool: Mapped[list] = mapped_column(JSON)
    policy: Mapped[dict] = mapped_column(JSON)
    config: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Job(Base):
    __tablename__ = "matching_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    window_id: Mapped[int] = mapped_column(
        ForeignKey("matching_windows.id"), unique=True
    )
    key: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    window_id: Mapped[int] = mapped_column(ForeignKey("matching_windows.id"))
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    score: Mapped[float] = mapped_column(Float)
    breakdown: Mapped[dict] = mapped_column(JSON)
    algorithm: Mapped[str] = mapped_column(String(30), default="hm-1.0")
    __table_args__ = (UniqueConstraint("window_id", "number"),)


class Member(Base):
    __tablename__ = "team_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    window_id: Mapped[int] = mapped_column(ForeignKey("matching_windows.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("window_id", "user_id"),)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(String(500))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    expires: Mapped[datetime] = mapped_column(DateTime)


class Mail(Base):
    __tablename__ = "mail_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(String(3000))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ImportRecord(Base):
    __tablename__ = "luma_import_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("luma_imports.id"))
    guest_id: Mapped[str] = mapped_column(String(200))
    raw: Mapped[dict] = mapped_column(JSON)
    normalized: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("import_id", "guest_id"),)
