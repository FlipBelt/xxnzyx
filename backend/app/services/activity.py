from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Activity, ChallengeScore, Registration, RewardTier


def activity_query() -> Select[tuple[Activity]]:
    return (
        select(Activity)
        .options(
            selectinload(Activity.score_items),
            selectinload(Activity.reward_tiers),
            selectinload(Activity.media_assets),
        )
        .order_by(desc(Activity.id))
    )


async def get_activity_by_slug(session: AsyncSession, slug: str) -> Activity:
    activity = await session.scalar(activity_query().where(Activity.slug == slug))
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")
    return activity


async def get_current_activity(session: AsyncSession) -> Activity:
    activity = await session.scalar(activity_query().where(Activity.status == "active"))
    if activity is None:
        activity = await session.scalar(activity_query())
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="当前没有活动")
    return activity


def reward_for_score(score: int, tiers: Iterable[RewardTier]) -> RewardTier | None:
    for tier in sorted(tiers, key=lambda item: item.min_score, reverse=True):
        if score >= tier.min_score and (tier.max_score is None or score <= tier.max_score):
            return tier
    return None


def mask_name(value: str) -> str:
    if len(value) <= 1:
        return "*"
    return f"{value[0]}*"


def public_participant_name(registration: Registration, activity: Activity) -> str:
    mode = activity.leaderboard_name_mode
    if mode == "plate_only":
        return registration.number_plate
    if mode == "masked_name":
        return mask_name(registration.name_snapshot)
    return f"{registration.number_plate} {mask_name(registration.name_snapshot)}"


def serialize_activity(activity: Activity) -> dict[str, object]:
    return {
        "id": activity.id,
        "slug": activity.slug,
        "title": activity.title,
        "description": activity.description,
        "status": activity.status,
        "challenge_duration_seconds": activity.challenge_duration_seconds,
        "challenge_limit": activity.challenge_limit,
        "draw_threshold": activity.draw_threshold,
        "leaderboard_name_mode": activity.leaderboard_name_mode,
        "rules_text": activity.rules_text,
        "score_items": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "points": item.points,
                "max_quantity": item.max_quantity,
                "is_required": item.is_required,
                "is_hidden_bonus": item.is_hidden_bonus,
                "appear_at_seconds_remaining": item.appear_at_seconds_remaining,
                "display_order": item.display_order,
            }
            for item in sorted(activity.score_items, key=lambda item: item.display_order)
            if item.is_active
        ],
        "reward_tiers": [
            {
                "id": tier.id,
                "min_score": tier.min_score,
                "max_score": tier.max_score,
                "title": tier.title,
                "prize_name": tier.prize_name,
                "description": tier.description,
                "display_order": tier.display_order,
            }
            for tier in sorted(activity.reward_tiers, key=lambda tier: tier.display_order)
            if tier.is_active
        ],
        "media_assets": [
            {
                "kind": media.kind,
                "label": media.label,
                "url": media.public_url,
                "object_key": media.object_key,
                "mime_type": media.mime_type,
            }
            for media in activity.media_assets
        ],
    }


async def leaderboard_entries(
    session: AsyncSession,
    activity: Activity,
    *,
    include_private: bool = False,
) -> list[dict[str, object]]:
    result = await session.execute(
        select(Registration)
        .join(ChallengeScore)
        .where(Registration.activity_id == activity.id)
        .options(selectinload(Registration.score))
        .order_by(ChallengeScore.total_score.desc(), Registration.id.asc())
    )
    registrations = list(result.scalars())
    entries: list[dict[str, object]] = []
    rank = 0
    previous_score: int | None = None
    for index, registration in enumerate(registrations, start=1):
        assert registration.score is not None
        if previous_score != registration.score.total_score:
            rank = index
            previous_score = registration.score.total_score
        reward = reward_for_score(registration.score.total_score, activity.reward_tiers)
        entry: dict[str, object] = {
            "rank": rank,
            "registration_id": registration.id,
            "display_name": public_participant_name(registration, activity),
            "number_plate": registration.number_plate,
            "score": registration.score.total_score,
            "title": reward.title if reward else None,
        }
        if include_private:
            # The admin view is authenticated and needs the original registration
            # fields to reconcile a score with the paper/onsite sign-in sheet.
            # Public leaderboard responses intentionally remain masked.
            entry["name"] = registration.name_snapshot
            entry["phone"] = registration.phone_snapshot
        entries.append(entry)
    return entries
