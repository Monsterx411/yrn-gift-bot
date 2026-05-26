"""
Bot entry point.
- python -m bot.main           → runs in polling mode (development)
- python -m web.asgi           → runs in webhook mode (production)
"""
import logging
from telegram import Update, BotCommand, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application

from bot.config import config
from database.engine import init_db

# Import all handler modules
from bot.handlers import start, cards, balance, admin, webapp, payments

logger = logging.getLogger(__name__)


def register_all_handlers(application: Application) -> None:
    """Register all handler modules on the application."""
    start.register(application)
    cards.register(application)
    balance.register(application)
    admin.register(application)
    webapp.register(application)
    payments.register(application)


async def set_commands_and_menu(application: Application) -> None:
    """Set bot commands and menu button."""
    commands = [
        BotCommand("start", "Start the bot & main menu"),
        BotCommand("cards", "Generate a gift card"),
        BotCommand("balance", "Check your stats"),
        BotCommand("history", "View generated cards"),
        BotCommand("buy", "Purchase cards with Stars"),
        BotCommand("redeem", "Redeem a gift card code"),
        BotCommand("app", "Open WebApp"),
        BotCommand("admin", "Admin panel"),
        BotCommand("help", "Show help"),
    ]
    await application.bot.set_my_commands(commands)

    if config.WEBAPP_URL:
        await application.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎁 Gift Cards",
                web_app=WebAppInfo(url=config.WEBAPP_URL),
            )
        )
    logger.info("Bot commands and menu button set.")


def build_application() -> Application:
    """Build and configure the Application (shared by polling & webhook modes)."""
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set. Check your .env file.")

    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    register_all_handlers(application)
    return application


async def post_init(application: Application) -> None:
    """Initialize database and set commands."""
    await init_db()
    await set_commands_and_menu(application)


async def post_shutdown(application: Application) -> None:
    """Cleanup."""
    from database.engine import close_db
    await close_db()
    logger.info("Database connections closed.")


def main() -> None:
    """Run in polling mode (development)."""
    import asyncio

    application = build_application()

    # Attach lifecycle handlers for polling mode
    # (for webhook mode, these are handled by server.py's lifespan)
    async def startup_wrapper(app: Application):
        await post_init(app)
    async def shutdown_wrapper(app: Application):
        await post_shutdown(app)

    application.post_init = startup_wrapper
    application.post_shutdown = shutdown_wrapper

    logger.info("🤖 Gift Card Bot starting in POLLING mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    )
    main()