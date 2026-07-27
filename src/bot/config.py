import os

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"{name} is not set")
    return value


BOT_TOKEN = require_env("BOT_TOKEN")

DB_NAME = os.getenv("DB_NAME", "database.db")
MAX_MONITOR_COUNT = int(os.getenv("MAX_MONITOR_COUNT", "20"))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "900"))
MAX_CONCURRENT_SCRAPES = int(os.getenv("MAX_CONCURRENT_SCRAPES", "5"))
ALLOWED_DOMAIN = "olx.kz"
