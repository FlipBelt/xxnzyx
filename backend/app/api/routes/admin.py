from __future__ import annotations

from secrets import SystemRandom

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import DbSession, get_current_admin
from app.models import (
    ActivityConfigVersion,
    AdminUser,
    AuditLog,
    ChallengeScore,
    DrawResult,
    MediaAsset,
    Participant,
    ParticipantIdentity,
    Registration,
    RewardTier,
    ScoreItem,
)
from app.schemas.activity import (
    ActivitySettingsUpdate,
    AdminLoginRequest,
    AdminRegistrationCreate,
    MediaAssetUpdate,
    RewardTierUpdate,
    ScoreCreate,
    ScoreItemUpdate,
)
from app.services.activity import (
    get_current_activity,
    leaderboard_entries,
    reward_for_score,
    serialize_activity,
)
from app.services.scoring import ScoreValidationError, save_score
from app.services.security import create_access_token, verify_password
from app.services.storage import StorageConfigurationError, get_object_storage

router = APIRouter(prefix="/admin")
secure_random = SystemRandom()


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def admin_payload(admin: AdminUser) -> dict[str, object]:
    return {
        "id": admin.id,
        "username": admin.username,
        "display_name": admin.display_name,
        "role": admin.role,
    }


async def add_config_audit(
    session: AsyncSession,
    activity_id: int,
    admin_id: int,
    category: str,
    payload: object,
) -> None:
    latest_version = await session.scalar(
        select(func.max(ActivityConfigVersion.version)).where(
            ActivityConfigVersion.activity_id == activity_id
        )
    )
    version = (latest_version or 0) + 1
    session.add(
        ActivityConfigVersion(
            activity_id=activity_id,
            version=version,
            category=category,
            payload={"data": payload},
            changed_by_admin_id=admin_id,
        )
    )
    session.add(
        AuditLog(
            activity_id=activity_id,
            admin_user_id=admin_id,
            action=f"config.{category}",
            entity_type="activity_config",
            entity_id=str(activity_id),
            after_data={"data": payload},
        )
    )


def ensure_tiers_valid(tiers: list[RewardTierUpdate]) -> list[RewardTierUpdate]:
    if not tiers:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="至少需要一个奖励区间")
    sorted_tiers = sorted(tiers, key=lambda item: item.min_score)
    expected_min = 0
    for tier in sorted_tiers:
        if tier.min_score != expected_min:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="奖励区间必须从0分开始且不能断档")
        if tier.max_score is None:
            if tier is not sorted_tiers[-1]:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="无上限区间只能位于最后")
            continue
        if tier.max_score < tier.min_score:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="奖励区间上限不能小于下限")
        expected_min = tier.max_score + 1
    return sorted_tiers


@router.post("/login")
async def admin_login(payload: AdminLoginRequest, session: DbSession) -> dict[str, object]:
    admin = await session.scalar(select(AdminUser).where(AdminUser.username == payload.username.strip()))
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return {
        "access_token": create_access_token(f"admin:{admin.id}", admin.role),
        "token_type": "bearer",
        "admin": admin_payload(admin),
    }


@router.get("/dashboard")
async def dashboard(session: DbSession, _: AdminUser = Depends(get_current_admin)) -> dict[str, object]:
    activity = await get_current_activity(session)
    registered_count = await session.scalar(
        select(func.count()).select_from(Registration).where(Registration.activity_id == activity.id)
    )
    scored_count = await session.scalar(
        select(func.count())
        .select_from(Registration)
        .where(Registration.activity_id == activity.id, Registration.status == "scored")
    )
    high_score_count = await session.scalar(
        select(func.count())
        .select_from(Registration)
        .join(ChallengeScore)
        .where(Registration.activity_id == activity.id, ChallengeScore.total_score >= activity.draw_threshold)
    )
    highest_score = await session.scalar(
        select(func.max(ChallengeScore.total_score))
        .join(Registration)
        .where(Registration.activity_id == activity.id)
    )
    return {
        "activity": {"id": activity.id, "title": activity.title, "status": activity.status},
        "registered_count": registered_count or 0,
        "scored_count": scored_count or 0,
        "pending_score_count": (registered_count or 0) - (scored_count or 0),
        "draw_qualified_count": high_score_count or 0,
        "highest_score": highest_score or 0,
    }


@router.get("/registrations")
async def list_registrations(
    session: DbSession,
    _: AdminUser = Depends(get_current_admin),
    keyword: str | None = Query(default=None, max_length=80),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    query = (
        select(Registration)
        .where(Registration.activity_id == activity.id)
        .options(selectinload(Registration.score).selectinload(ChallengeScore.details))
        .order_by(Registration.id.desc())
    )
    if keyword:
        normalized = "".join(char for char in keyword if char.isdigit())
        query = query.where(
            (Registration.name_snapshot.contains(keyword.strip()))
            | (Registration.number_plate.ilike(f"%{keyword.strip()}%"))
            | (Registration.phone_snapshot.contains(normalized or keyword.strip()))
        )
    rows = list((await session.execute(query)).scalars())
    return {
        "items": [
            {
                "id": registration.id,
                "name": registration.name_snapshot,
                "phone": registration.phone_snapshot,
                "number_plate": registration.number_plate,
                "status": registration.status,
                "score": registration.score.total_score if registration.score else None,
                "score_details": [
                    {
                        "score_item_id": detail.score_item_id,
                        "quantity": detail.quantity,
                        "subtotal": detail.subtotal,
                    }
                    for detail in (registration.score.details if registration.score else [])
                ],
            }
            for registration in rows
        ]
    }


@router.post("/registrations", status_code=status.HTTP_201_CREATED)
async def create_manual_registration(
    payload: AdminRegistrationCreate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    """现场数据失联时，由工作人员补录，随后可直接登记成绩。"""
    activity = await get_current_activity(session)
    name = payload.name.strip()
    phone = normalize_phone(payload.phone)
    number_plate = payload.number_plate.strip()
    if len(phone) != 11:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="手机号必须为11位数字")
    duplicate = await session.scalar(
        select(Registration.id).where(
            Registration.activity_id == activity.id,
            (Registration.phone_snapshot == phone) | (Registration.number_plate == number_plate),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号或号码牌已存在，请直接查询后录分")
    participant = Participant(name=name, phone=phone)
    session.add(participant)
    await session.flush()
    session.add(
        ParticipantIdentity(
            participant_id=participant.id,
            channel="admin",
            external_id=f"admin:{activity.id}:{participant.id}",
        )
    )
    registration = Registration(
        activity_id=activity.id,
        participant_id=participant.id,
        name_snapshot=name,
        phone_snapshot=phone,
        number_plate=number_plate,
    )
    session.add(registration)
    await session.flush()
    session.add(
        AuditLog(
            activity_id=activity.id,
            admin_user_id=admin.id,
            action="registration.manual_create",
            entity_type="registration",
            entity_id=str(registration.id),
            after_data={"name": name, "phone": phone, "number_plate": number_plate, "source": "admin_manual"},
        )
    )
    await session.commit()
    return {"id": registration.id, "name": name, "phone": phone, "number_plate": number_plate, "status": registration.status, "score": None}


@router.post("/scores", status_code=status.HTTP_201_CREATED)
async def create_or_update_score(
    payload: ScoreCreate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    try:
        score = await save_score(session, activity, payload, admin)
    except ScoreValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    reward = reward_for_score(score.total_score, activity.reward_tiers)
    return {
        "id": score.id,
        "registration_id": score.registration_id,
        "total_score": score.total_score,
        "reward": {"title": reward.title, "prize_name": reward.prize_name} if reward else None,
        "details": [
            {"score_item_id": detail.score_item_id, "quantity": detail.quantity, "subtotal": detail.subtotal}
            for detail in score.details
        ],
    }


@router.put("/scores/{registration_id}")
async def update_score(
    registration_id: int,
    payload: ScoreCreate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    """Explicitly modify an existing score without allowing a new score to be created."""
    activity = await get_current_activity(session)
    payload = payload.model_copy(update={"registration_id": registration_id})
    try:
        score = await save_score(session, activity, payload, admin, update_only=True)
    except ScoreValidationError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "尚未录入成绩" in message else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=message) from exc
    reward = reward_for_score(score.total_score, activity.reward_tiers)
    return {
        "id": score.id,
        "registration_id": score.registration_id,
        "total_score": score.total_score,
        "reward": {"title": reward.title, "prize_name": reward.prize_name} if reward else None,
        "details": [
            {"score_item_id": detail.score_item_id, "quantity": detail.quantity, "subtotal": detail.subtotal}
            for detail in score.details
        ],
    }


@router.delete("/scores")
async def delete_all_scores(
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, int]:
    """Clear all entered scores for the current activity while keeping registrations."""
    activity = await get_current_activity(session)
    rows = list(
        (
            await session.execute(
                select(ChallengeScore)
                .join(Registration, Registration.id == ChallengeScore.registration_id)
                .where(Registration.activity_id == activity.id)
                .options(selectinload(ChallengeScore.details), selectinload(ChallengeScore.registration))
            )
        ).scalars()
    )
    registration_ids = [score.registration_id for score in rows]
    for score in rows:
        score.registration.status = "registered"
        await session.delete(score)
    session.add(
        AuditLog(
            activity_id=activity.id,
            admin_user_id=admin.id,
            action="score.bulk_delete",
            entity_type="challenge_score",
            entity_id=str(activity.id),
            before_data={"registration_ids": registration_ids, "count": len(registration_ids)},
            after_data={"deleted_count": len(registration_ids)},
        )
    )
    await session.commit()
    return {"deleted_count": len(registration_ids)}


@router.delete("/scores/{registration_id}")
async def delete_score(
    registration_id: int,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, int | str]:
    """Remove one entered score and return the registration to the waiting state."""
    activity = await get_current_activity(session)
    registration = await session.scalar(
        select(Registration)
        .where(Registration.id == registration_id, Registration.activity_id == activity.id)
        .options(selectinload(Registration.score).selectinload(ChallengeScore.details))
    )
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="参赛者不存在")
    score = registration.score
    if score is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该参赛者尚未录入成绩")
    before_data = {
        "total_score": score.total_score,
        "details": [
            {"score_item_id": detail.score_item_id, "quantity": detail.quantity, "subtotal": detail.subtotal}
            for detail in score.details
        ],
    }
    registration.status = "registered"
    await session.delete(score)
    session.add(
        AuditLog(
            activity_id=activity.id,
            admin_user_id=admin.id,
            action="score.delete",
            entity_type="challenge_score",
            entity_id=str(registration.id),
            before_data=before_data,
            after_data={"registration_status": registration.status},
        )
    )
    await session.commit()
    return {"registration_id": registration.id, "status": registration.status}


@router.get("/leaderboard")
async def admin_leaderboard(session: DbSession, _: AdminUser = Depends(get_current_admin)) -> dict[str, object]:
    activity = await get_current_activity(session)
    return {"entries": await leaderboard_entries(session, activity, include_private=True)}


@router.get("/draw/candidates")
async def draw_candidates(session: DbSession, _: AdminUser = Depends(get_current_admin)) -> dict[str, object]:
    activity = await get_current_activity(session)
    entries = await leaderboard_entries(session, activity)
    return {"threshold": activity.draw_threshold, "items": [item for item in entries if item["score"] >= activity.draw_threshold]}


@router.post("/draw")
async def run_draw(session: DbSession, admin: AdminUser = Depends(get_current_admin)) -> dict[str, object]:
    activity = await get_current_activity(session)
    existing = list(
        (
            await session.execute(
                select(DrawResult)
                .where(DrawResult.activity_id == activity.id)
                .order_by(DrawResult.prize_rank)
            )
        ).scalars()
    )
    if existing:
        return {
            "already_drawn": True,
            "results": [
                {"prize_rank": item.prize_rank, "registration_id": item.registration_id, "prize_name": item.prize_name}
                for item in existing
            ],
        }
    candidate_ids = list(
        (
            await session.execute(
                select(Registration.id)
                .join(ChallengeScore)
                .where(Registration.activity_id == activity.id, ChallengeScore.total_score >= activity.draw_threshold)
            )
        ).scalars()
    )
    if len(candidate_ids) < 2:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="符合抽奖资格的参赛者不足两人")
    winners = secure_random.sample(candidate_ids, 2)
    prize_names = ["价值998元越野全套装备", "价值399元越野袋鼠裤"]
    results = [
        DrawResult(
            activity_id=activity.id,
            registration_id=winner_id,
            prize_rank=index,
            prize_name=prize_names[index - 1],
            drawn_by_admin_id=admin.id,
        )
        for index, winner_id in enumerate(winners, start=1)
    ]
    session.add_all(results)
    session.add(
        AuditLog(
            activity_id=activity.id,
            admin_user_id=admin.id,
            action="draw.run",
            entity_type="draw",
            entity_id=str(activity.id),
            after_data={"winner_registration_ids": winners},
        )
    )
    await session.commit()
    return {
        "already_drawn": False,
        "results": [
            {"prize_rank": item.prize_rank, "registration_id": item.registration_id, "prize_name": item.prize_name}
            for item in results
        ],
    }


@router.get("/config")
async def get_config(session: DbSession, _: AdminUser = Depends(get_current_admin)) -> dict[str, object]:
    return serialize_activity(await get_current_activity(session))


@router.put("/config/activity")
async def update_activity_settings(
    payload: ActivitySettingsUpdate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    for field, value in payload.model_dump().items():
        setattr(activity, field, value)
    await add_config_audit(session, activity.id, admin.id, "activity", payload.model_dump())
    await session.commit()
    return serialize_activity(await get_current_activity(session))


@router.put("/config/reward-tiers")
async def replace_reward_tiers(
    payload: list[RewardTierUpdate],
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    tiers = ensure_tiers_valid(payload)
    for tier in list(activity.reward_tiers):
        await session.delete(tier)
    await session.flush()
    for tier in tiers:
        session.add(RewardTier(activity_id=activity.id, is_active=True, **tier.model_dump()))
    await add_config_audit(session, activity.id, admin.id, "reward_tiers", [item.model_dump() for item in tiers])
    await session.commit()
    return serialize_activity(await get_current_activity(session))


@router.post("/config/score-items", status_code=status.HTTP_201_CREATED)
async def create_score_item(
    payload: ScoreItemUpdate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    existing = await session.scalar(
        select(ScoreItem).where(ScoreItem.activity_id == activity.id, ScoreItem.code == payload.code)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="道具编码已存在")
    item = ScoreItem(activity_id=activity.id, is_active=True, **payload.model_dump())
    session.add(item)
    await session.flush()
    await add_config_audit(session, activity.id, admin.id, "score_item.create", payload.model_dump())
    await session.commit()
    return {"id": item.id, **payload.model_dump()}


@router.put("/config/score-items/{item_id}")
async def update_score_item(
    item_id: int,
    payload: ScoreItemUpdate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    item = await session.scalar(select(ScoreItem).where(ScoreItem.id == item_id, ScoreItem.activity_id == activity.id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="道具不存在")
    before = {"name": item.name, "points": item.points, "max_quantity": item.max_quantity}
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    await add_config_audit(
        session,
        activity.id,
        admin.id,
        "score_item.update",
        {"id": item_id, "before": before, "after": payload.model_dump()},
    )
    await session.commit()
    return {"id": item.id, **payload.model_dump()}


@router.put("/config/media")
async def upsert_media_asset(
    payload: MediaAssetUpdate,
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, object]:
    activity = await get_current_activity(session)
    media = await session.scalar(
        select(MediaAsset).where(MediaAsset.activity_id == activity.id, MediaAsset.kind == payload.kind)
    )
    if media is None:
        media = MediaAsset(activity_id=activity.id, **payload.model_dump())
        session.add(media)
    else:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(media, field, value)
    await add_config_audit(session, activity.id, admin.id, "media", payload.model_dump())
    await session.commit()
    return {"kind": media.kind, "url": media.public_url, "label": media.label}


@router.post("/config/media/upload", status_code=status.HTTP_201_CREATED)
async def upload_media_asset(
    session: DbSession,
    admin: AdminUser = Depends(get_current_admin),
    kind: str = Form(..., min_length=1, max_length=40),
    label: str = Form(..., min_length=1, max_length=100),
    file: UploadFile = File(...),
) -> dict[str, object]:
    """Upload a configured activity asset to the selected storage backend and save its media record."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请选择要上传的媒体文件")
    content = await file.read(100 * 1024 * 1024 + 1)
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="媒体文件不能超过 100MB")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上传的媒体文件为空")

    activity = await get_current_activity(session)
    try:
        stored = await run_in_threadpool(
            get_object_storage().upload_media,
            activity.id,
            file.filename,
            content,
            file.content_type,
        )
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="媒体存储失败") from exc

    media = await session.scalar(
        select(MediaAsset).where(MediaAsset.activity_id == activity.id, MediaAsset.kind == kind.strip())
    )
    if media is None:
        media = MediaAsset(
            activity_id=activity.id,
            kind=kind.strip(),
            label=label.strip(),
            object_key=stored.object_key,
            public_url=stored.public_url,
            mime_type=stored.mime_type,
        )
        session.add(media)
    else:
        media.label = label.strip()
        media.object_key = stored.object_key
        media.public_url = stored.public_url
        media.mime_type = stored.mime_type
    await add_config_audit(
        session,
        activity.id,
        admin.id,
        "media.upload",
        {"kind": media.kind, "label": media.label, "object_key": stored.object_key, "mime_type": stored.mime_type},
    )
    await session.commit()
    return {
        "kind": media.kind,
        "label": media.label,
        "url": media.public_url,
        "object_key": media.object_key,
        "mime_type": media.mime_type,
    }
