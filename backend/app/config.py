import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, List, Union, Any

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "FirstPatch AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Ollama Local AI Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gemma4:e2b"
    OLLAMA_FALLBACK_MODEL: str = "gemma2:2b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    
    MODEL_CONTEXT_TOKENS: int = 8192
    MODEL_OUTPUT_TOKENS: int = 1536
    MAX_RETRIEVED_CHUNKS: int = 12
    MAX_EVIDENCE_CHARS: int = 24000
    MAX_CONVERSATION_TURNS: int = 8
    
    # SQLite Database (uses /tmp on Vercel to ensure write permissions in serverless environments)
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH",
        "/tmp/firstpatch.db" if os.getenv("VERCEL") else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firstpatch.db")
    )
    
    # GitHub API Configuration
    GITHUB_TOKEN: Optional[str] = None
    
    # DigitalOcean Gradient™ AI Agentic Cloud Configuration
    DO_GRADIENT_API_KEY: Optional[str] = None
    DO_GRADIENT_WORKSPACE_ID: Optional[str] = None
    AI_INFERENCE_PROVIDER: str = "ollama"  # 'ollama' or 'digitalocean_gradient'
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import json
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

settings = Settings()
