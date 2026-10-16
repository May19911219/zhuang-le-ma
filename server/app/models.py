from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    """返回带时区的当前 UTC 时间。"""
    return datetime.now(timezone.utc)


class Software(Base):
    __tablename__ = "software"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="generic")
    source_ref: Mapped[str] = mapped_column(String(300), default="")
    install_type: Mapped[str] = mapped_column(String(40), default="script")
    official_url: Mapped[str] = mapped_column(String(500), default="")
    aliases: Mapped[str] = mapped_column(Text, default="[]")
    fallback_versions: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VersionEntry(Base):
    __tablename__ = "versions"
    __table_args__ = (UniqueConstraint("software_id", "version", name="uq_software_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    software_id: Mapped[int] = mapped_column(ForeignKey("software.id"), index=True)
    version: Mapped[str] = mapped_column(String(80))
    is_latest_stable: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(40), default="cache")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("software_id", "version", "platform", name="uq_plan_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    software_id: Mapped[int] = mapped_column(ForeignKey("software.id"), index=True)
    version: Mapped[str] = mapped_column(String(80))
    platform: Mapped[str] = mapped_column(String(20))
    markdown: Mapped[str] = mapped_column(Text, default="")
    script: Mapped[str] = mapped_column(Text, default="")
    script_shell: Mapped[str] = mapped_column(String(20), default="")
    install_type: Mapped[str] = mapped_column(String(40), default="script")
    official_url: Mapped[str] = mapped_column(String(500), default="")
    generated_by: Mapped[str] = mapped_column(String(20), default="fallback")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SelectionStat(Base):
    __tablename__ = "selection_stats"
    __table_args__ = (
        UniqueConstraint("software_id", "version", "platform", name="uq_selection"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    software_id: Mapped[int] = mapped_column(ForeignKey("software.id"), index=True)
    version: Mapped[str] = mapped_column(String(80))
    platform: Mapped[str] = mapped_column(String(20))
    count: Mapped[int] = mapped_column(Integer, default=0)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    token: Mapped[str] = mapped_column(String(80), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
