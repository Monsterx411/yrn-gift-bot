#!/usr/bin/env python3
"""
Register/update the webhook URL with Telegram.
Usage: python scripts/set_webhook.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import config
from telegram import Bot


async def main():
    if not config.BOT_TOKEN:
        print("❌ BOT_TOKEN not set in .env")
        return
    if not config.WEBHOOK_URL:
        print("❌ WEBHOOK_URL not set in .env")
        return

    bot = Bot(token=config.BOT_TOKEN)

    # Delete current webhook first
    await bot.delete_webhook(drop_pending_updates=True)
    print("🗑️ Existing webhook deleted")

    # Set new webhook
    secret = config.WEBHOOK_SECRET_TOKEN or None
    await bot.set_webhook(
        url=config.WEBHOOK_URL,
        secret_token=secret,
        allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"],
        max_connections=40,
    )
    print(f"✅ Webhook set to: {config.WEBHOOK_URL}")
    if secret:
        print(f"🔐 Secret token configured")

    # Verify
    info = await bot.get_webhook_info()
    print(f"\n📋 Webhook Info:")
    print(f"   URL:           {info.url}")
    print(f"   Pending:       {info.pending_update_count}")
    print(f"   Max Conn:      {info.max_connections}")
    print(f"   Allowed:       {info.allowed_updates}")


if __name__ == "__main__":
    asyncio.run(main())