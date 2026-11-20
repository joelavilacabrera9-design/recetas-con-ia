"""Configuración de la aplicación leída desde variables de entorno (.env)."""

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _database_url() -> str:
    """Usa DATABASE_URL si existe; si no, la construye con las variables MYSQL_*."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("MYSQL_USER", "recetas")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "db")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "recetas")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    llm_timeout_seconds: float
    llm_json_mode: bool
    llm_mock: bool
    app_url: str


@lru_cache
def get_settings() -> Settings:
    jwt_secret = os.getenv("JWT_SECRET", "")
    if len(jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET no está definido o es muy corto (mínimo 32 caracteres). "
            "Genera uno con: openssl rand -hex 32"
        )
    return Settings(
        database_url=_database_url(),
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
        ),
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).rstrip("/"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        llm_json_mode=_bool(os.getenv("LLM_JSON_MODE"), default=True),
        llm_mock=_bool(os.getenv("LLM_MOCK"), default=False),
        app_url=os.getenv("APP_URL", "http://localhost:8000"),
    )
