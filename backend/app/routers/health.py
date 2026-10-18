from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.app.config import settings
from backend.app.services.ollama_service import ollama_service
from backend.app.database import get_db

router = APIRouter(tags=["Health & Models"])

class ModelUpdateSchema(BaseModel):
    model_name: str
    embed_model_name: Optional[str] = None

@router.get("/api/health")
async def health_check():
    db_status = "healthy"
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as e:
        db_status = f"error: {str(e)}"

    ollama_status = await ollama_service.get_status()

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
        "ollama": ollama_status
    }

@router.get("/api/models/status")
async def get_model_status():
    return await ollama_service.get_status()

@router.get("/api/models")
async def list_models():
    status = await ollama_service.get_status()
    return {
        "installed_models": status.get("installed_models", []),
        "active_model": status.get("active_model", settings.OLLAMA_MODEL),
        "embed_model": status.get("embed_model", settings.OLLAMA_EMBED_MODEL)
    }

@router.post("/api/models/health-check")
async def test_model_inference():
    status = await ollama_service.get_status()
    if not status["online"]:
        raise HTTPException(status_code=503, detail=f"Ollama is offline: {status.get('error')}")

    try:
        res = await ollama_service.generate_response(
            prompt="Respond in 1 sentence: What is the primary purpose of unit testing in open-source software?",
            temperature=0.1
        )
        return {
            "status": "success",
            "model": res["model"],
            "test_output": res["response"].strip()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/api/settings/models")
async def update_active_model(data: ModelUpdateSchema):
    settings.OLLAMA_MODEL = data.model_name
    if data.embed_model_name:
        settings.OLLAMA_EMBED_MODEL = data.embed_model_name

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO model_configs (key, value, updated_at) VALUES ('active_model', ?, datetime('now'))", (data.model_name,))

    return {
        "status": "updated",
        "active_model": settings.OLLAMA_MODEL,
        "embed_model": settings.OLLAMA_EMBED_MODEL
    }
