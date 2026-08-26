from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    challenge_duration_seconds: Mapped[int] = mapped_column(Integer, default=40)
    challenge_limit: Mapped[int] = mapped_column(Integer, default=1)
    draw_threshold: Mapped[int] = mapped_column(Integer, default=45)
    leaderboard_name_mode: Mapped[str] = mapped_column(String(30), default="plate_masked_name")
    rules_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    score_items: Mapped[list[ScoreItem]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    reward_tiers: Mapped[list[RewardTier]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    media_assets: Mapped[list[MediaAsset]] = relationship(back_populates="activity", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    identities: Mapped[list[ParticipantIdentity]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    registrations: Mapped[list[Registration]] = relationship(back_populates="participant")


class ParticipantIdentity(Base):
    __tablename__ = "participant_identities"
    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_identity_channel_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    participant: Mapped[Participant] = relationship(back_populates="identities")


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("activity_id", "participant_id", name="uq_registration_activity_participant"),
        UniqueConstraint("activity_id", "phone_snapshot", name="uq_registration_activity_phone"),
        UniqueConstraint("activity_id", "number_plate", name="uq_registration_activity_plate"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), index=True)
    name_snapshot: Mapped[str] = mapped_column(String(80))
    phone_snapshot: Mapped[str] = mapped_column(String(32))
    number_plate: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="registered", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    activity: Mapped[Activity] = relationship()
    participant: Mapped[Participant] = relationship(back_populates="registrations")
    score: Mapped[ChallengeScore | None] = relationship(
        back_populates="registration", cascade="all, delete-orphan", uselist=False
    )


class ScoreItem(Base):
    __tablename__ = "score_items"
    __table_args__ = (UniqueConstraint("activity_id", "code", name="uq_score_item_activity_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(80))
    points: Mapped[int] = mapped_column(Integer)
    max_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden_bonus: Mapped[bool] = mapped_column(Boolean, default=False)
    appear_at_seconds_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    activity: Mapped[Activity] = relationship(back_populates="score_items")


class RewardTier(Base):
    __tablename__ = "reward_tiers"
    __table_args__ = (UniqueConstraint("activity_id", "display_order", name="uq_reward_tier_activity_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    min_score: Mapped[int] = mapped_column(Integer)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(80))
    prize_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    activity: Mapped[Activity] = relationship(back_populates="reward_tiers")


class ChallengeScore(Base):
    __tablename__ = "challenge_scores"
    __table_args__ = (UniqueConstraint("registration_id", name="uq_score_registration"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id", ondelete="CASCADE"))
    total_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    entered_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    config_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    registration: Mapped[Registration] = relationship(back_populates="score")
    details: Mapped[list[ChallengeScoreDetail]] = relationship(
        back_populates="score", cascade="all, delete-orphan"
    )


class ChallengeScoreDetail(Base):
    __tablename__ = "challenge_score_details"
    __table_args__ = (UniqueConstraint("challenge_score_id", "score_item_id", name="uq_score_detail_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_score_id: Mapped[int] = mapped_column(ForeignKey("challenge_scores.id", ondelete="CASCADE"))
    score_item_id: Mapped[int] = mapped_column(ForeignKey("score_items.id"))
    item_name_snapshot: Mapped[str] = mapped_column(String(80))
    points_snapshot: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer)

    score: Mapped[ChallengeScore] = relationship(back_populates="details")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("activity_id", "kind", name="uq_media_activity_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(100))
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_url: Mapped[str] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    activity: Mapped[Activity] = relationship(back_populates="media_assets")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(30), default="scorer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DrawResult(Base):
    __tablename__ = "draw_results"
    __table_args__ = (
        UniqueConstraint("activity_id", "prize_rank", name="uq_draw_activity_prize_rank"),
        UniqueConstraint("activity_id", "registration_id", name="uq_draw_activity_registration"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    registration_id: Mapped[int] = mapped_column(ForeignKey("registrations.id", ondelete="CASCADE"))
    prize_rank: Mapped[int] = mapped_column(Integer)
    prize_name: Mapped[str] = mapped_column(String(160))
    drawn_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    drawn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ActivityConfigVersion(Base):
    __tablename__ = "activity_config_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    changed_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
