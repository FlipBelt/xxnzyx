from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession, get_current_participant
from app.core.config import get_settings
from app.models import ChallengeScore, Participant, ParticipantIdentity, Registration
from app.schemas.activity import ParticipantAuthRequest, RegistrationCreate
from app.services.activity import (
    get_activity_by_slug,
    get_current_activity,
    leaderboard_entries,
    reward_for_score,
    serialize_activity,
)
from app.services.security import create_access_token

router = APIRouter()


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def validate_channel(channel: str) -> None:
    if channel == "wechat" and get_settings().app_env not in {"development", "test"}:
        raise HTTPException(status_code=400, detail="微信身份授权尚未配置，请使用现场H5入口")


def registration_result(registration: Registration, *, existing: bool = False) -> dict[str, object]:
    return {
        "registration_id": registration.id,
        "status": registration.status,
        "access_token": create_access_token(f"participant:{registration.participant_id}", "participant"),
        "token_type": "bearer",
        "already_registered": existing,
    }


def verify_registration(registration: Registration, name: str, number_plate: str) -> None:
    # 恢复必须核对完整报名资料；不再凭手机号签发身份。
    if registration.name_snapshot != name.strip() or registration.number_plate != number_plate.strip():
        raise HTTPException(status_code=409, detail="报名资料与已有记录不一致，请联系现场工作人员核对")


@router.get("/activity/current")
async def current_activity(session: DbSession) -> dict[str, object]:
    activity = await get_current_activity(session)
    return serialize_activity(activity)


@router.post("/participant/login")
async def participant_login(payload: ParticipantAuthRequest, session: DbSession) -> dict[str, object]:
    validate_channel(payload.channel)
    activity = await get_activity_by_slug(session, payload.activity_slug)
    phone = normalize_phone(payload.external_id)
    if payload.channel not in {"h5", "dingtalk"} or len(phone) != 11:
        raise HTTPException(status_code=400, detail="请通过H5填写完整报名资料恢复，或联系现场工作人员")
    registration = await session.scalar(
        select(Registration).where(Registration.activity_id == activity.id, Registration.phone_snapshot == phone)
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="未找到匹配的报名资料")
    verify_registration(registration, payload.name, payload.number_plate)
    return registration_result(registration, existing=True)


@router.post("/registrations", status_code=status.HTTP_201_CREATED)
async def create_registration(payload: RegistrationCreate, session: DbSession) -> dict[str, object]:
    validate_channel(payload.channel)
    activity = await get_activity_by_slug(session, payload.activity_slug)
    activity_id = activity.id
    name, number_plate = payload.name.strip(), payload.number_plate.strip()
    phone = normalize_phone(payload.phone)
    external_id = payload.external_id.strip()
    if not name or not number_plate or len(phone) != 11:
        raise HTTPException(status_code=422, detail="请填写姓名、11位手机号和本场参赛号码牌")
    if payload.channel in {"h5", "dingtalk"}:
        if normalize_phone(external_id) != phone:
            raise HTTPException(status_code=422, detail="H5身份需与报名手机号一致")
        external_id = phone

    existing = await session.scalar(
        select(Registration).where(Registration.activity_id == activity_id, Registration.phone_snapshot == phone)
    )
    if existing is not None:
        verify_registration(existing, name, number_plate)
        return registration_result(existing, existing=True)
    if activity.status != "active":
        raise HTTPException(status_code=409, detail="活动当前不可报名")
    duplicate_plate = await session.scalar(
        select(Registration).where(Registration.activity_id == activity_id, Registration.number_plate == number_plate)
    )
    if duplicate_plate is not None:
        if duplicate_plate.phone_snapshot == phone:
            verify_registration(duplicate_plate, name, number_plate)
            return registration_result(duplicate_plate, existing=True)
        raise HTTPException(status_code=409, detail="报名资料与已有记录冲突，请联系现场工作人员核对")

    try:
        identity = await session.scalar(
            select(ParticipantIdentity).where(
                ParticipantIdentity.channel == payload.channel, ParticipantIdentity.external_id == external_id
            )
        )
        if identity is None:
            participant = Participant(name=name, phone=phone)
            session.add(participant)
            await session.flush()
            participant_id = participant.id
            session.add(ParticipantIdentity(participant_id=participant_id, channel=payload.channel, external_id=external_id))
        else:
            participant_id = identity.participant_id
        registration = Registration(
            activity_id=activity_id, participant_id=participant_id, name_snapshot=name,
            phone_snapshot=phone, number_plate=number_plate,
        )
        session.add(registration)
        await session.commit()
        await session.refresh(registration)
        return registration_result(registration)
    except IntegrityError:
        # 两个并发请求可能同时通过前置查询；数据库唯一约束是最终去重边界。
        await session.rollback()
        existing = await session.scalar(
            select(Registration).where(Registration.activity_id == activity_id, Registration.phone_snapshot == phone)
        )
        if existing is not None:
            verify_registration(existing, name, number_plate)
            return registration_result(existing, existing=True)
        raise HTTPException(status_code=409, detail="报名资料与已有记录冲突，请联系现场工作人员核对") from None


@router.get("/me")
async def get_me(session: DbSession, participant: Participant = Depends(get_current_participant)) -> dict[str, object]:
    activity = await get_current_activity(session)
    registration = await session.scalar(
        select(Registration)
        .where(Registration.activity_id == activity.id, Registration.participant_id == participant.id)
        .options(selectinload(Registration.score).selectinload(ChallengeScore.details))
    )
    if registration is None:
        return {"registered": False, "activity_slug": activity.slug}

    leaderboard = await leaderboard_entries(session, activity)
    score = registration.score
    rank_entry = next((item for item in leaderboard if item["registration_id"] == registration.id), None)
    reward = reward_for_score(score.total_score, activity.reward_tiers) if score else None
    official_rank = rank_entry["rank"] if rank_entry else None
    return {
        "registered": True,
        "registration_id": registration.id,
        "name": registration.name_snapshot,
        "number_plate": registration.number_plate,
        "status": registration.status,
        "score": score.total_score if score else None,
        # rank remains for older clients. The explicit fields let the mobile UI add a
        # separate, approved display strategy later without disguising the official rank.
        "rank": official_rank,
        "official_rank": official_rank,
        "display_rank": None,
        "display_title": reward.title if reward is not None else None,
        "reward": (
            {"title": reward.title, "prize_name": reward.prize_name} if reward is not None else None
        ),
        "draw_qualified": bool(score and score.total_score >= activity.draw_threshold),
        "details": [
            {
                "item_name": detail.item_name_snapshot,
                "points": detail.points_snapshot,
                "quantity": detail.quantity,
                "subtotal": detail.subtotal,
            }
            for detail in (score.details if score else [])
        ],
    }


@router.get("/leaderboard")
async def get_leaderboard(session: DbSession) -> dict[str, object]:
    activity = await get_current_activity(session)
    return {"activity": activity.title, "entries": await leaderboard_entries(session, activity)}
