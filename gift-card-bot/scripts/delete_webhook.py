#!/usr/bin/env python3
"""
Delete the webhook (revert to polling).
Usage: python scripts/delete_webhook.py
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import config
from telegram import Bot


async def main():
    if not config.BOT_TOKEN:
        print("❌ BOT_TOKEN not set")
        return

    bot = Bot(token=config.BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook deleted. Bot will now use polling.")


if __name__ == "__main__":
    asyncio.run(main())