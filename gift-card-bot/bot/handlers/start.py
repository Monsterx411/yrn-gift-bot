from telegram import Update, BotCommand
from telegram.ext import CommandHandler, ContextTypes

from utils.keyboards import main_menu_keyboard
from database.repository import get_or_create_user


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message and main menu."""
    user = update.effective_user

    # Register/get user in DB
    from database.engine import get_session
    async with get_session() as session:
        await get_or_create_user(
            session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        await session.commit()

    welcome = (
        f"🎁 *Welcome to Gift Card Generator, {user.first_name}!*\n\n"
        f"I help you generate secure gift card codes.\n\n"
        f"💳 *Pay with Telegram Stars* — generate premium cards\n"
        f"🌐 *WebApp* — full visual interface inside Telegram\n"
        f"🔐 *Secure codes* — cryptographically generated\n\n"
        f"Use the buttons below or tap the menu button!"
    )

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help."""
    text = (
        "*Available Commands*\n\n"
        "`/start` — Welcome & main menu\n"
        "`/cards` — Generate a gift card\n"
        "`/balance` — Check your balance & stats\n"
        "`/history` — View your generated cards\n"
        "`/redeem <code>` — Redeem a gift card\n"
        "`/app` — Open the WebApp\n"
        "`/help` — This message\n\n"
        "_Cards are generated with cryptographically secure random codes._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def register(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))