from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes
import json
import logging

from database.repository import generate_card, get_or_create_user
from database.engine import get_session
from services.webapp_auth import validate_webapp_init_data

logger = logging.getLogger(__name__)


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle data received from the Telegram WebApp."""
    web_app_data = update.effective_message.web_app_data
    if not web_app_data:
        return

    user_id = update.effective_user.id
    raw_data = web_app_data.data

    logger.info(f"WebApp data received from user {user_id}")

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from WebApp: {raw_data}")
        await update.effective_message.reply_text("Invalid data received from WebApp.")
        return

    action = data.get("action")

    if action == "generate_card":
        card_type = data.get("card_type", "basic")

        async with get_session() as session:
            # Register user
            await get_or_create_user(
                session,
                telegram_id=user_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
            )

            # Also register via initData if available
            init_data = data.get("initData")
            if init_data:
                validated = validate_webapp_init_data(init_data)
                if validated:
                    logger.info(f"WebApp initData validated for user {user_id}")
                else:
                    logger.warning(f"WebApp initData validation FAILED for user {user_id}")

            card = await generate_card(session, user_id, card_type, metadata={"source": "webapp"})
            if card:
                await session.commit()

                text = (
                    f"✅ *Card Generated via WebApp!*\n\n"
                    f"🎁 *{card.template.name}*\n"
                    f"`{card.code}`\n"
                    f"💵 *${card.amount/100:.2f}*\n\n"
                    f"Code saved — share it with the recipient."
                )
                await update.effective_message.reply_text(text, parse_mode="Markdown")
            else:
                await update.effective_message.reply_text(
                    "❌ Invalid card type. Please try again."
                )

    elif action == "redeem_card":
        code = data.get("code", "").strip().upper()
        if not code:
            await update.effective_message.reply_text("No code provided.")
            return

        async with get_session() as session:
            from database.repository import get_card_by_code, redeem_card
            card = await get_card_by_code(session, code)
            if not card:
                await update.effective_message.reply_text("❌ Card not found.")
                return

            if card.status.value != "active":
                await update.effective_message.reply_text(
                    f"❌ Card is already *{card.status.value}*.",
                    parse_mode="Markdown"
                )
                return

            await redeem_card(session, code, str(user_id))
            await session.commit()

            await update.effective_message.reply_text(
                f"✅ *Card Redeemed!*\n\n"
                f"`{card.code}` — *${card.amount/100:.2f}*\n"
                f"The value has been added to your account.",
                parse_mode="Markdown"
            )

    else:
        logger.warning(f"Unknown WebApp action: {action}")


def register(application):
    application.add_handler(
        MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data)
    )