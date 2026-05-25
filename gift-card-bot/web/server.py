"""
FastAPI webhook server for production Telegram bot deployment.
Runs alongside python-telegram-bot's Application to handle
incoming updates via webhook instead of long polling.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import Application

from bot.config import config
from database.engine import init_db, close_db
from bot.main import build_application

logger = logging.getLogger(__name__)

# Global bot application instance
ptb_app: Application | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + build + start bot app. Shutdown: stop bot + close DB."""
    global ptb_app

    logger.info("Starting up webhook server...")

    # Initialize database
    await init_db()

    # Build the bot Application (registers all handlers)
    ptb_app = build_application()

    # Initialize but don't start polling — we'll feed updates via webhook
    await ptb_app.initialize()

    # Set the webhook on Telegram's side
    webhook_url = config.WEBHOOK_URL
    secret_token = config.WEBHOOK_SECRET_TOKEN

    if webhook_url:
        await ptb_app.bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token if secret_token else None,
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info(f"Webhook set to: {webhook_url}")
    else:
        logger.warning("WEBHOOK_URL not set — webhook not registered")

    yield

    # Shutdown
    logger.info("Shutting down webhook server...")
    if ptb_app:
        await ptb_app.shutdown()
    await close_db()


app = FastAPI(
    title="Gift Card Bot Webhook",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "bot_running": ptb_app is not None}


@app.post("/webhook")
async def webhook(request: Request):
    """
    Receive Telegram update via webhook.
    Telegram sends POST requests with an Update object.
    """
    global ptb_app

    if ptb_app is None:
        logger.error("Bot application not initialized")
        raise HTTPException(status_code=503, detail="Bot not ready")

    # Verify secret token if configured
    secret_token = config.WEBHOOK_SECRET_TOKEN
    if secret_token:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != secret_token:
            logger.warning("Invalid secret token in webhook request")
            raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        body = await request.json()
        update = Update.de_json(body, ptb_app.bot)
        await ptb_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        return JSONResponse(
            status_code=200,  # Always return 200 to avoid re-delivery
            content={"ok": False, "error": str(e)},
        )