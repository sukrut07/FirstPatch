"""
FirstPatch AI — Application Configuration
Reads from environment variables with validation.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    app_version: str = "0.1.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # GitHub
    github_token: str = ""
    github_http_timeout: int = 30
    max_issues_per_repo: int = 100
    max_files_to_analyze: int = 50
    repo_cache_ttl_seconds: int = 3600

    # AI Provider
    ai_provider: Literal["google_ai_studio", "local_ollama", "none"] = "none"
    google_ai_api_key: str = ""
    google_ai_model: str = "gemma-4-31b-it"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"

    # Database
    database_url: str = "sqlite+aiosqlite:///./firstpatch.db"

    # Security
    secret_key: str = "CHANGE_ME_generate_a_real_secret_key"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def github_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"FirstPatch-AI/{self.app_version}",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    @field_validator("secret_key")
    @classmethod
    def warn_default_secret(cls, v: str) -> str:
        if v == "CHANGE_ME_generate_a_real_secret_key":
            import logging
            logging.getLogger(__name__).warning(
                "SECRET_KEY is set to its default placeholder. "
                "Generate a real secret for production."
            )
        return v

    @model_validator(mode="after")
    def validate_ai_provider_credentials(self) -> "Settings":
        if self.ai_provider == "google_ai_studio" and not self.google_ai_api_key:
            import logging
            logging.getLogger(__name__).warning(
                "AI_PROVIDER=google_ai_studio but GOOGLE_AI_API_KEY is not set. "
                "Falling back to deterministic mode."
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
