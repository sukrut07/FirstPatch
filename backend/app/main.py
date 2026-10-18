"""
FirstPatch AI — Backend Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.routes import health, repositories, issues, mentor, verification
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    yield
    # Shutdown: nothing to clean up yet


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FirstPatch AI API",
        description="Evidence-backed open-source contribution mentor",
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS — allow configured frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health.router, prefix="/api")
    app.include_router(repositories.router, prefix="/api/repositories")
    app.include_router(issues.router, prefix="/api/issues")
    app.include_router(mentor.router, prefix="/api/mentor")
    app.include_router(verification.router, prefix="/api/verification")

    return app


app = create_app()
