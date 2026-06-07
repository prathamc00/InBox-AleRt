from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "InboxAlert"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"

    # ── JWT (RS256) ────────────────────────────────────────────
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Encryption (AES-256-GCM) ──────────────────────────────
    TOKEN_ENCRYPTION_KEY: str  # 64-char hex string = 32 bytes

    # ── Database ───────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://...

    # ── Redis ──────────────────────────────────────────────────
    REDIS_URL: str

    # ── Google OAuth ───────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    GOOGLE_CLOUD_PROJECT: str = "inboxalertd"

    # ── Microsoft OAuth ────────────────────────────────────────
    MICROSOFT_CLIENT_ID: str
    MICROSOFT_CLIENT_SECRET: str
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/auth/microsoft/callback"



    # ── AI ─────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── Webhook Security ───────────────────────────────────────
    OUTLOOK_WEBHOOK_CLIENT_STATE: str = ""

    # ── Stripe ────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── WhatsApp Business API (Meta Cloud) ────────────────────
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""

    @field_validator("GEMINI_API_KEY", "WHATSAPP_ACCESS_TOKEN", mode="before")
    @classmethod
    def _strip_whitespace(cls, value):
        """Strip leading/trailing whitespace from API keys (common .env copy-paste issue)."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"dev", "debug", "true", "1", "yes", "on"}:
                return True
        return value

    @property
    def jwt_private_key(self) -> str:
        """Unescape \\n literals stored in env vars."""
        return self.JWT_PRIVATE_KEY.replace("\\n", "\n")

    @property
    def jwt_public_key(self) -> str:
        return self.JWT_PUBLIC_KEY.replace("\\n", "\n")

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
