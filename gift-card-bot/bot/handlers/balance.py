from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from database.repository import get_user_by_id, get_user_cards, get_or_create_user
from database.engine import get_session
from services.stats import get_user_stats
from utils.formatters import format_user_profile, format_card_list
from utils.keyboards import main_menu_keyboard, back_keyboard


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's balance and stats."""
    user_id = update.effective_user.id

    async with get_session() as session:
        user = await get_user_by_id(session, user_id)
        if not user:
            await update.message.reply_text("Please /start first to register.")
            return

        stats = await get_user_stats(session, user_id)

    text = format_user_profile(user, stats)
    await update.message.reply_text(text, parse_mode="Markdown")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's generated cards history."""
    user_id = update.effective_user.id

    async with get_session() as session:
        cards = await get_user_cards(session, user_id, limit=20)

    if not cards:
        await update.message.reply_text(
            "No cards generated yet. Use /cards to start!",
            reply_markup=main_menu_keyboard()
        )
        return

    text = "*📋 Your Recent Gift Cards*\n\n" + format_card_list(cards)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=back_keyboard())


async def menu_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler for balance menu button."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    async with get_session() as session:
        user = await get_user_by_id(session, user_id)
        stats = await get_user_stats(session, user_id) if user else {}

    if not user:
        await query.edit_message_text("Please /start first.")
        return

    text = format_user_profile(user, stats)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


async def menu_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler for history menu button."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    async with get_session() as session:
        cards = await get_user_cards(session, user_id, limit=20)

    if not cards:
        await query.edit_message_text(
            "No cards yet. Generate one from the menu!",
            reply_markup=main_menu_keyboard()
        )
        return

    text = "*📋 Your Recent Gift Cards*\n\n" + format_card_list(cards)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


def register(application):
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CallbackQueryHandler(menu_balance_handler, pattern="^menu_balance$"))
    application.add_handler(CallbackQueryHandler(menu_history_handler, pattern="^menu_history$"))