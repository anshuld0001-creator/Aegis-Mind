"""
Application configuration.
Reads from environment variables (.env) with safe local defaults for the prototype.
"""
import http
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AEGIS MIND"
    APP_TAGLINE: str = "Predictive Welfare Intelligence for Those Who Serve."
    ENV: str = os.getenv("ENV", "development")

    # Database - defaults to local SQLite for the student prototype.
    # Swap DATABASE_URL to a postgres:// URL to point at PostgreSQL without any code changes.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aegis_mind.db")

    # JWT / auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_" + os.urandom(8).hex())
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # CORS — kept as a plain comma-separated string and split where it's
    # used (see main.py). pydantic-settings tries to JSON-decode list-typed
    # env values, which breaks on a plain string like "http://a,http://b".
    CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://192.168.29.123:5173",
]

    # Risk thresholds (configurable early-warning thresholds)
    RISK_THRESHOLD_MODERATE: int = 40
    RISK_THRESHOLD_HIGH: int = 65
    RISK_THRESHOLD_CRITICAL: int = 85

    # AI MITRA — optional external AI provider. Left blank, AI Mitra runs
    # entirely on its built-in rule-based engine (app/mitra/engine.py).
    # Never referenced from any frontend code — server-side only.
    AI_PROVIDER_API_KEY: str = os.getenv("AI_PROVIDER_API_KEY", "")
    STT_API_KEY: str = os.getenv("STT_API_KEY", "")
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
