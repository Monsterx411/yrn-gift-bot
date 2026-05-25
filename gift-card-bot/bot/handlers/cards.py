from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import logging

from database.repository import get_active_templates, generate_card, get_or_create_user
from database.engine import get_session
from utils.keyboards import card_template_keyboard, main_menu_keyboard
from utils.formatters import format_card_display

logger = logging.getLogger(__name__)


async def cards_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available gift card templates."""
    async with get_session() as session:
        templates = await get_active_templates(session)

    if not templates:
        await update.message.reply_text("No card templates available right now.")
        return

    text = "*🎁 Select a Gift Card Type:*\n\nChoose a template below to generate your card."
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=card_template_keyboard(templates)
    )


async def handle_card_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle template selection callback."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu_generate":
        async with get_session() as session:
            templates = await get_active_templates(session)
        text = "*🎁 Select a Gift Card Type:*"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=card_template_keyboard(templates)
        )
        return

    if data == "menu_back":
        await query.edit_message_text(
            "*🎁 Main Menu*",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return

    if data.startswith("gen_"):
        template_key = data[4:]
        user_id = update.effective_user.id

        async with get_session() as session:
            # Register user if needed
            await get_or_create_user(
                session,
                telegram_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
            )

            card = await generate_card(session, user_id, template_key)
            if card:
                await session.commit()

                text = (
                    f"✅ *Gift Card Generated!*\n\n"
                    f"{format_card_display(card)}\n\n"
                    f"📋 *Code:* `{card.code}`\n"
                    f"💵 *Value:* `${card.amount/100:.2f}`\n"
                    f"📌 Share this code with recipients!"
                )

                keyboard = [
                    [InlineKeyboardButton("🎫 Generate Another", callback_data="menu_generate")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_back")],
                ]
                await query.edit_message_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "❌ Template not available. Please try another.",
                    reply_markup=card_template_keyboard(
                        await get_active_templates(session)
                    )
                )


def register(application):
    application.add_handler(CommandHandler("cards", cards_command))
    application.add_handler(CallbackQueryHandler(handle_card_selection, pattern="^(menu_generate|menu_back|gen_)"))