from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Activity, AdminUser, AuditLog, ChallengeScore, ChallengeScoreDetail, Registration
from app.schemas.activity import ScoreCreate, ScoreSubmission
from app.services.activity import reward_for_score


class ScoreValidationError(ValueError):
    """Raised when submitted item quantities violate an activity configuration."""


class ScoreConflictError(ValueError):
    """A guarded score write was based on stale or different information."""


def score_version(score: ChallengeScore | None) -> str | None:
    if score is None:
        return None
    updated = score.updated_at
    return f"{score.id}:{(updated if updated.tzinfo else updated.replace(tzinfo=UTC)).astimezone(UTC).isoformat()}"


def scoring_rules_version(activity: Activity) -> str:
    rows = sorted((item.id, item.name, item.points, item.max_quantity) for item in activity.score_items if item.is_active)
    return sha256(json.dumps(rows).encode()).hexdigest()


def score_details(score: ChallengeScore | None) -> list[dict[str, int]]:
    return [
        {"score_item_id": detail.score_item_id, "quantity": detail.quantity, "subtotal": detail.subtotal}
        for detail in (score.details if score else [])
    ]


async def find_score_operation(
    session: AsyncSession, activity_id: int, registration_id: int, admin_id: int, operation_id: str,
) -> dict | None:
    return await session.scalar(select(AuditLog.after_data).where(
        AuditLog.activity_id == activity_id,
        AuditLog.entity_type == "challenge_score",
        AuditLog.entity_id == str(registration_id),
        AuditLog.admin_user_id == admin_id,
        AuditLog.action.in_(("score.create", "score.update")),
        AuditLog.after_data["operation_id"].as_string() == operation_id,
    ))


async def save_score(
    session: AsyncSession,
    activity: Activity,
    payload: ScoreCreate,
    admin: AdminUser,
    *,
    update_only: bool = False,
) -> dict[str, object]:
    result = await session.execute(
        select(Registration)
        .where(Registration.id == payload.registration_id, Registration.activity_id == activity.id)
        .options(selectinload(Registration.score).selectinload(ChallengeScore.details))
        .with_for_update()
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise ScoreValidationError("未找到该活动的参赛者")

    operation_data = {}
    if isinstance(payload, ScoreSubmission):
        operation_id = str(payload.operation_id)
        request_data = {
            "expected_version": payload.expected_version,
            "rules_version": payload.rules_version,
            "items": [entry.model_dump() for entry in sorted(payload.items, key=lambda item: item.score_item_id)],
        }
        existing = await find_score_operation(session, activity.id, registration.id, admin.id, operation_id)
        if existing is not None:
            if existing["request"] != request_data:
                raise ScoreConflictError("此提交编号已用于其他内容，请重新核对")
            return existing["receipt"]
        if score_version(registration.score) != payload.expected_version:
            raise ScoreConflictError("这位选手的成绩已更新，请核对后保存")
        if scoring_rules_version(activity) != payload.rules_version:
            raise ScoreConflictError("计分规则已更新，请核对数量和预计总分")
        operation_data = {"operation_id": operation_id, "request": request_data}

    active_items = {item.id: item for item in activity.score_items if item.is_active}
    received_ids = [entry.score_item_id for entry in payload.items]
    if len(received_ids) != len(set(received_ids)):
        raise ScoreValidationError("同一道具不能重复录入")
    unknown_ids = set(received_ids) - set(active_items)
    if unknown_ids:
        raise ScoreValidationError("存在无效道具")

    quantities = {entry.score_item_id: entry.quantity for entry in payload.items}
    total = 0
    details: list[ChallengeScoreDetail] = []
    existing_details = {}
    previous_data: dict[str, object] | None = None
    if registration.score is not None:
        previous_data = {
            "total_score": registration.score.total_score,
            "details": [
                {"item": detail.item_name_snapshot, "quantity": detail.quantity, "subtotal": detail.subtotal}
                for detail in registration.score.details
            ],
        }
        existing_details = {detail.score_item_id: detail for detail in registration.score.details}
        for detail in list(registration.score.details):
            if detail.score_item_id not in active_items:
                registration.score.details.remove(detail)

    for item in active_items.values():
        quantity = quantities.get(item.id, 0)
        if item.max_quantity is not None and quantity > item.max_quantity:
            raise ScoreValidationError(f"{item.name}最多可录入{item.max_quantity}个")
        subtotal = quantity * item.points
        total += subtotal
        detail = existing_details.get(item.id)
        if detail is None:
            detail = ChallengeScoreDetail(score_item_id=item.id)
            details.append(detail)
        detail.item_name_snapshot = item.name
        detail.points_snapshot = item.points
        detail.quantity = quantity
        detail.subtotal = subtotal

    if registration.score is None:
        if update_only:
            raise ScoreValidationError("该参赛者尚未录入成绩，不能执行修改")
        score = ChallengeScore(
            registration_id=registration.id,
            total_score=total,
            entered_by_admin_id=admin.id,
            config_version=1,
            details=details,
        )
        session.add(score)
        action = "score.create"
    else:
        score = registration.score
        score.total_score = total
        score.updated_at = datetime.now(UTC)
        score.entered_by_admin_id = admin.id
        score.details.extend(details)
        action = "score.update"

    registration.status = "scored"
    await session.flush()
    reward = reward_for_score(total, activity.reward_tiers)
    receipt = {
        "id": score.id,
        "registration_id": registration.id,
        "total_score": total,
        "reward": {"title": reward.title, "prize_name": reward.prize_name} if reward else None,
        "details": score_details(score),
        "version": score_version(score),
    }
    if operation_data:
        operation_data["receipt"] = receipt
    session.add(
        AuditLog(
            activity_id=activity.id,
            admin_user_id=admin.id,
            action=action,
            entity_type="challenge_score",
            entity_id=str(registration.id),
            before_data=previous_data,
            after_data={
                "total_score": total,
                "details": [
                    {"item": detail.item_name_snapshot, "quantity": detail.quantity, "subtotal": detail.subtotal}
                    for detail in score.details
                ],
                **operation_data,
            },
        )
    )
    await session.commit()
    return receipt
