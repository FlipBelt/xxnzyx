from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import DbSession, get_current_participant
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


@router.get("/activity/current")
async def current_activity(session: DbSession) -> dict[str, object]:
    activity = await get_current_activity(session)
    return serialize_activity(activity)


@router.post("/participant/login")
async def participant_login(payload: ParticipantAuthRequest, session: DbSession) -> dict[str, str]:
    identity = await session.scalar(
        select(ParticipantIdentity).where(
            ParticipantIdentity.channel == payload.channel,
            ParticipantIdentity.external_id == payload.external_id.strip(),
        )
    )
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未报名，请先完成报名")
    return {
        "access_token": create_access_token(f"participant:{identity.participant_id}", "participant"),
        "token_type": "bearer",
    }


@router.post("/registrations", status_code=status.HTTP_201_CREATED)
async def create_registration(payload: RegistrationCreate, session: DbSession) -> dict[str, object]:
    activity = await get_activity_by_slug(session, payload.activity_slug)
    if activity.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="活动当前不可报名")

    name = payload.name.strip()
    number_plate = payload.number_plate.strip()
    phone = normalize_phone(payload.phone)
    external_id = payload.external_id.strip()
    if len(phone) != 11:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="手机号必须为11位数字")
    if payload.channel in {"h5", "dingtalk"} and normalize_phone(external_id) != phone:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="H5身份需与报名手机号一致")

    identity = await session.scalar(
        select(ParticipantIdentity).where(
            ParticipantIdentity.channel == payload.channel,
            ParticipantIdentity.external_id == external_id,
        )
    )
    if identity is None:
        participant = Participant(name=name, phone=phone)
        session.add(participant)
        await session.flush()
        identity = ParticipantIdentity(
            participant_id=participant.id,
            channel=payload.channel,
            external_id=external_id,
        )
        session.add(identity)
    else:
        participant = await session.get(Participant, identity.participant_id)
        assert participant is not None

    duplicate_identity = await session.scalar(
        select(Registration.id).where(
            Registration.activity_id == activity.id,
            (Registration.participant_id == participant.id)
            | (Registration.phone_snapshot == phone),
        )
    )
    if duplicate_identity is not None:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已报名，可恢复原报名")

    duplicate_plate = await session.scalar(
        select(Registration.id).where(
            Registration.activity_id == activity.id,
            Registration.number_plate == number_plate,
        )
    )
    if duplicate_plate is not None:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该号码牌已被使用")

    registration = Registration(
        activity_id=activity.id,
        participant_id=participant.id,
        name_snapshot=name,
        phone_snapshot=phone,
        number_plate=number_plate,
    )
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    return {
        "registration_id": registration.id,
        "status": registration.status,
        "access_token": create_access_token(f"participant:{participant.id}", "participant"),
        "token_type": "bearer",
    }


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
