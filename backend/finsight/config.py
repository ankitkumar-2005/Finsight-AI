import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    DEBUG = _bool("FLASK_DEBUG", os.getenv("FLASK_ENV", "development") == "development")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    DB_NAME = os.getenv("MYSQL_DATABASE", "finsight")
    DB_USER = os.getenv("MYSQL_USER", "finsight_app")
    DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    DEMO_RESET_MODE = _bool("DEMO_RESET_MODE", DEBUG)
    RESET_TOKEN_TTL_MINUTES = int(os.getenv("RESET_TOKEN_TTL_MINUTES", "20"))
    CORS_ORIGINS = [value.strip() for value in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5182").split(",") if value.strip()]
