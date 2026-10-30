from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal AI Dashboard API"
    database_url: str = "sqlite:///./data/dashboard.db"
    frontend_origin: str = "http://localhost:3000"
    file_storage_dir: str = "./data/files"
    max_resume_size_mb: int = Field(default=10, ge=1, le=50)
    calendar_encryption_key: SecretStr | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    ollama_timeout_seconds: int = Field(default=45, ge=5, le=180)

    @field_validator("ollama_base_url", "ollama_model")
    @classmethod
    def normalize_optional_string(cls, value: str | None) -> str | None:
        normalized = value.strip() if value else None
        return normalized or None

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "OLLAMA_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment"
            )
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("OLLAMA_BASE_URL contains an invalid port") from exc
        return value.rstrip("/")

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
