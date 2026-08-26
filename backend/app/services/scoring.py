from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Activity, AdminUser, AuditLog, ChallengeScore, ChallengeScoreDetail, Registration
from app.schemas.activity import ScoreCreate


class ScoreValidationError(ValueError):
    """Raised when submitted item quantities violate an activity configuration."""


async def save_score(
    session: AsyncSession,
    activity: Activity,
    payload: ScoreCreate,
    admin: AdminUser,
) -> ChallengeScore:
    result = await session.execute(
        select(Registration)
        .where(Registration.id == payload.registration_id, Registration.activity_id == activity.id)
        .options(selectinload(Registration.score).selectinload(ChallengeScore.details))
        .with_for_update()
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise ScoreValidationError("未找到该活动的参赛者")

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
    for item in active_items.values():
        quantity = quantities.get(item.id, 0)
        if item.max_quantity is not None and quantity > item.max_quantity:
            raise ScoreValidationError(f"{item.name}最多可录入{item.max_quantity}个")
        subtotal = quantity * item.points
        total += subtotal
        details.append(
            ChallengeScoreDetail(
                score_item_id=item.id,
                item_name_snapshot=item.name,
                points_snapshot=item.points,
                quantity=quantity,
                subtotal=subtotal,
            )
        )

    previous_data: dict[str, object] | None = None
    if registration.score is None:
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
        previous_data = {
            "total_score": score.total_score,
            "details": [
                {"item": detail.item_name_snapshot, "quantity": detail.quantity, "subtotal": detail.subtotal}
                for detail in score.details
            ],
        }
        score.total_score = total
        score.entered_by_admin_id = admin.id
        score.details.clear()
        score.details.extend(details)
        action = "score.update"

    registration.status = "scored"
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
                    for detail in details
                ],
            },
        )
    )
    await session.commit()

    result = await session.execute(
        select(ChallengeScore)
        .where(ChallengeScore.id == score.id)
        .options(selectinload(ChallengeScore.details))
    )
    return result.scalar_one()
