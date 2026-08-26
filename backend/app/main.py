from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.services.seed import seed_demo_data

settings = get_settings()
PROJECT_ROOT = settings.local_upload_dir.parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Reserve one place for startup and shutdown resources."""
    settings.local_upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.app_env in {"development", "test"}:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            await seed_demo_data(session, settings)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")
app.mount("/uploads", StaticFiles(directory=settings.local_upload_dir), name="uploads")
