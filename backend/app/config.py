import os
from functools import lru_cache
from typing import List, Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    app_name: str = "Vernis Art Intelligence API"
    environment: str = "development"
    app_debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # API Keys
    openai_api_key: str = ""
    image_model: str = "gpt-image-2.5-sunburst"
    image_fallback_model: str = "gpt-image-2.5-flare"
    image_output_format: str = "webp"
    openai_timeout_seconds: float = 180.0
    generated_assets_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "generated"
    )

    # Canonical application persistence. Supabase-hosted Postgres is supported
    # through a regular direct connection; tests override this with SQLite.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:55432/vernis"
    database_schema: str = "vernis"
    database_echo: bool = False
    redis_url: str = "redis://127.0.0.1:56379/0"

    # Private asset storage. Local mode is intentionally development-only.
    storage_backend: Literal["local", "s3"] = "local"
    storage_root: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "storage"
    )
    storage_bucket: str = "vernis-private"
    storage_endpoint_url: str = ""
    storage_region: str = "us-east-1"
    storage_access_key_id: str = ""
    storage_secret_access_key: str = ""
    storage_signing_secret: str = "development-only-change-me-before-production"
    upload_max_bytes: int = 50 * 1024 * 1024
    upload_intent_ttl_seconds: int = 900

    # Fixed, clearly non-production identity used only when AUTH_REQUIRED=false.
    development_user_id: str = "00000000-0000-0000-0000-000000000001"
    development_user_email: str = "local@vernis.test"

    # Identity and authorization. Keep AUTH_REQUIRED false for local evaluation;
    # production deployments should enable it after configuring Supabase.
    supabase_url: str = ""
    auth_required: bool = False

    # Hosted billing. Secret and webhook keys are server-only.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_creator: str = ""
    stripe_price_studio: str = ""
    stripe_price_artist: str = ""
    stripe_price_professional: str = ""
    stripe_price_gallery: str = ""
    stripe_price_institution: str = ""
    stripe_price_enterprise: str = ""
    frontend_url: str = "http://localhost:5173"

    # Optional multi-agent advisory layer. Image creation never depends on it.
    crew_enabled: bool = False
    crew_model: str = "gpt-4o-mini"
    external_ai_text_enabled: bool = False

    # CORS Settings
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    rate_limit_per_minute: int = 240

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_deployment_security(self) -> "Settings":
        if self.auth_required and not self.supabase_url:
            raise ValueError("SUPABASE_URL is required when AUTH_REQUIRED=true")
        if self.environment == "production":
            if not self.auth_required:
                raise ValueError("AUTH_REQUIRED must be true in production")
            if self.storage_backend != "s3":
                raise ValueError("STORAGE_BACKEND must be s3 in production")
            if self.storage_signing_secret == "development-only-change-me-before-production":
                raise ValueError("STORAGE_SIGNING_SECRET must be replaced in production")
            if len(self.storage_signing_secret) < 32:
                raise ValueError("STORAGE_SIGNING_SECRET must contain at least 32 characters")
        return self

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
