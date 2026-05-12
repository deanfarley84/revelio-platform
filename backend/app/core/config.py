from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://vyre:vyre_secret@localhost:5432/vyre"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET: str = "change_this_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    AI_PROMPT_VERSION: str = "v1.0"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "vyre-files"
    AWS_REGION: str = "eu-west-2"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Reference prefix
    DIAGNOSTIC_REF_PREFIX: str = "RVL"

    # Email transport (optional). When SMTP_HOST is unset the email service
    # logs intent and no-ops, so invitations / notifications still work but
    # link delivery is manual until a provider is wired up.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "no-reply@outturn.io"
    EMAIL_FROM_NAME: str = "Outturn"
    PUBLIC_APP_URL: str = "https://vyre-frontend-38kb.onrender.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
