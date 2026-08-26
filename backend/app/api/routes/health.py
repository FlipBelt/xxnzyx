from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness check that does not depend on external services."""
    return {"status": "ok"}


@router.get("/health/database", status_code=status.HTTP_200_OK)
async def database_health_check(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Readiness check used after PostgreSQL is available."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
