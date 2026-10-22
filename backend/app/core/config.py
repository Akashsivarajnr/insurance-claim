import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_name: str = "ClaimFlow API"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = f"sqlite:///{(BASE_DIR / 'claimflow.db').as_posix()}"
    upload_dir: str = str(BASE_DIR / "uploads")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()

if not settings.secret_key or settings.secret_key.startswith("replace-with"):
    # No usable secret configured: create a temporary one so nothing is hardcoded.
    # Logins become invalid whenever the server restarts. Set SECRET_KEY in .env to keep them.
    settings.secret_key = secrets.token_urlsafe(48)
    print("[ClaimFlow] WARNING: SECRET_KEY not set in .env - using a temporary random key.")
