from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oc_logistics"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "oc-logistics"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"
    presign_expiry_seconds: int = 3600

    # Auth
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Seed
    seed_owner_email: str = "owner@example.com"
    seed_owner_password: str = "changeme"

    # External (Phase 3+)
    anthropic_api_key: str = ""
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    openclaw_backend_base_url: str = "http://localhost:8000"


settings = Settings()
