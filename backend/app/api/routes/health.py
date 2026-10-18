"""Health endpoint."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import AIProviderStatus, HealthResponse
from app.services.mentor.ai_provider import get_ai_provider

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Service health check. Returns version and provider status without exposing secrets."""
    settings = get_settings()
    provider = get_ai_provider()

    try:
        ai_status = await provider.health_check()
    except Exception:
        ai_status = AIProviderStatus.UNAVAILABLE

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        ai_provider=provider.provider_name,
        ai_provider_status=ai_status,
        github_authenticated=bool(settings.github_token),
    )
