from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.6-27b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/doc_pipeline"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,"
        "http://172.17.19.162:3000,http://172.17.19.162:3001"
    )

    upload_dir: str = "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
