from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    google_client_id: str | None = None
    gemini_api_key: str | None = None
    cors_origins: list[str] = ["http://localhost:5173"]
    redis_url: str = "redis://localhost:6379/0"
    # Dev/test stub root for LocalFileStorage (app/core/storage.py) — used when
    # Supabase settings below are unset (local dev/tests).
    local_storage_root: str = "./storage"
    # Supabase Storage (app/core/storage.py: SupabaseFileStorage). Service-role
    # key, not anon — this is privileged server-side access, never exposed to a
    # client. Leave both unset to keep using LocalFileStorage (e.g. tests).
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "documents"


@lru_cache
def get_settings() -> Settings:
    return Settings()
