from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "examate-rag"
    environment: str = "local"  # local | ci | production

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    fallback_model: str | None = None
    embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = 30.0
    llm_retries: int = 2

    chunk_size_chars: int = 1800
    chunk_overlap_chars: int = 200

    # Optional: set these to get estimated_cost_usd instead of null.
    llm_input_cost_per_1m: float | None = None
    llm_output_cost_per_1m: float | None = None
    embedding_cost_per_1m: float | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
