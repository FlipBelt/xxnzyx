from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models import AdminUser, Participant
from app.services.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return decode_access_token(credentials.credentials)


async def get_current_admin(
    session: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AdminUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    claims = decode_access_token(credentials.credentials)
    if claims["role"] not in {"admin", "scorer"} or not claims["sub"].startswith("admin:"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台访问权限")
    admin = await session.get(AdminUser, int(claims["sub"].split(":", 1)[1]))
    if admin is None or not admin.is_active or admin.role not in {"admin", "scorer"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="后台账号无效")
    return admin


async def get_administrator(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    if admin.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="此操作需要管理员权限")
    return admin


async def get_current_participant(
    session: DbSession,
    claims: dict[str, str] = Depends(get_token_claims),
) -> Participant:
    if claims["role"] != "participant" or not claims["sub"].startswith("participant:"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无用户访问权限")
    participant = await session.get(Participant, int(claims["sub"].split(":", 1)[1]))
    if participant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return participant
