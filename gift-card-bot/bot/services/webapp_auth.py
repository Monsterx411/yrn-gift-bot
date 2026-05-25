import hmac
import hashlib
import logging
from urllib.parse import unquote, parse_qs
from typing import Optional, Any

from bot.config import config

logger = logging.getLogger(__name__)


def validate_webapp_init_data(init_data: str) -> Optional[dict[str, Any]]:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    Returns parsed data dict if valid, None otherwise.
    
    Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not config.HMAC_SECRET_KEY:
        logger.warning("Missing init_data or HMAC_SECRET_KEY")
        return None

    try:
        parsed = {}
        for item in init_data.split('&'):
            if '=' not in item:
                continue
            key, value = item.split('=', 1)
            parsed[key] = unquote(value)

        received_hash = parsed.pop('hash', None)
        if not received_hash:
            logger.warning("No hash in init_data")
            return None

        # Build data check string
        data_check_items = sorted(parsed.items(), key=lambda x: x[0])
        data_check_string = '\n'.join(f"{k}={v}" for k, v in data_check_items)

        # Compute secret key: HMAC_SHA256(<bot_token>, "WebAppData")
        secret_key = hmac.new(
            config.BOT_TOKEN.encode(),
            b"WebAppData",
            hashlib.sha256
        ).digest()

        # Compute expected hash
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_hash != received_hash:
            logger.warning("WebApp init data validation FAILED")
            return None

        logger.info("WebApp init data validated successfully")
        return parsed

    except Exception as e:
        logger.error(f"WebApp validation error: {e}")
        return None