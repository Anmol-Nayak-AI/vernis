import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Config
    app_name: str = "AgentCanvas Studio API"
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

    # Identity and authorization. Keep AUTH_REQUIRED false for local evaluation;
    # production deployments should enable it after configuring Supabase.
    supabase_url: str = ""
    auth_required: bool = False

    # Hosted billing. Secret and webhook keys are server-only.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_creator: str = ""
    stripe_price_studio: str = ""
    stripe_price_enterprise: str = ""
    frontend_url: str = "http://localhost:5173"

    # Optional multi-agent advisory layer. Image creation never depends on it.
    crew_enabled: bool = False
    crew_model: str = "gpt-4o-mini"

    # CORS Settings
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    # Pydantic v2 configuration
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
