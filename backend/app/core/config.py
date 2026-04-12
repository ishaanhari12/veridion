from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # extra="ignore" means unknown env vars (POSTGRES_USER etc.) are silently
    # ignored instead of causing a validation error.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Veridion API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://veridion:veridion_secret@db:5432/veridion"
    test_database_url: str = "postgresql://veridion:veridion_secret@db:5432/veridion_test"

    # JWT
    secret_key: str = "changeme_in_production_use_32_chars_minimum"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Fraud service
    fraud_service_url: str = "http://fraud:8001"
    fraud_block_threshold: float = 0.85
    fraud_flag_threshold: float = 0.50


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
