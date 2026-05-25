import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
    HMAC_SECRET_KEY: str = os.getenv("HMAC_SECRET_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/gift_cards.db")
    ADMIN_IDS: list[int] = [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ]
    PROVIDER_TOKEN: str = os.getenv("PROVIDER_TOKEN", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()