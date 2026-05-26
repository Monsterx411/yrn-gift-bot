from telegram import Update, LabeledPrice
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler,
    MessageHandler, filters, ContextTypes
)
import logging
import json
import uuid

from database.repository import (
    get_active_templates, get_template_by_key, generate_card,
    get_or_create_user, create_payment, complete_payment,
    get_payment_by_payload
)
from database.engine import get_session
from bot.config import config
from utils.keyboards import payment_keyboard, card_template_keyboard

logger = logging.getLogger(__name__)


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show templates available for purchase with Stars."""
    async with get_session() as session:
        templates = await get_active_templates(session)
        # Only show templates that cost Stars
        paid_templates = [t for t in templates if t.price_stars > 0]

    if not paid_templates:
        await update.message.reply_text("No paid templates available right now.")
        return

    text = "*💎 Purchase Gift Cards with Telegram Stars*\n\nSelect a card type to buy:"
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=card_template_keyboard(paid_templates)
    )


async def initiate_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment initiation from callback."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("buy_"):
        template_key = data[4:]

        async with get_session() as session:
            template = await get_template_by_key(session, template_key)

        if not template or template.price_stars <= 0:
            await query.edit_message_text("Template not available for purchase.")
            return

        user_id = update.effective_user.id
        payload = f"card_{template_key}_{uuid.uuid4().hex[:12]}"

        # Store the payload in context so we can look it up later
        if context.user_data is None:
            context.user_data = {}
        context.user_data["pending_payload"] = payload
        context.user_data["pending_template_key"] = template_key

        prices = [LabeledPrice(template.name, template.price_stars)]

        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"🎁 {template.name}",
            description=template.description or f"Purchase {template.name}",
            payload=payload,
            provider_token=config.PROVIDER_TOKEN or "",  # Empty for XTR
            currency="XTR",
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
        )

        await query.edit_message_text(
            f"💳 *Invoice sent!*\n\n"
            f"Please complete the payment for *{template.name}*\n"
            f"Cost: *{template.price_stars} ⭐*",
            parse_mode="Markdown"
        )


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre-checkout query — auto-approve."""
    query = update.pre_checkout_query
    payload = query.invoice_payload

    logger.info(f"PreCheckoutQuery: user={query.from_user.id}, payload={payload}")

    # Always approve — you can add validation here
    await query.answer(ok=True, error_message="Payment failed. Please try again.")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment — generate the card."""
    payment = update.effective_message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload
    charge_id = payment.telegram_payment_charge_id
    stars_amount = payment.total_amount

    logger.info(f"Successful payment: user={user_id}, payload={payload}, charge={charge_id}")

    async with get_session() as session:
        # Register user
        await get_or_create_user(
            session,
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
        )

        # Determine which template from payload
        if payload.startswith("card_"):
            template_key = payload.split("_")[1]
        else:
            template_key = "premium"  # fallback

        # Generate the card
        card = await generate_card(session, user_id, template_key)

        if card:
            # Create payment record
            payment_record = await create_payment(
                session, user_id, stars_amount, payload, card_id=card.id
            )
            payment_record.telegram_payment_charge_id = charge_id
            payment_record.status = "completed"
            payment_record.completed_at = None  # will be set by auto

            # Mark as completed
            from database.models import PaymentStatus
            payment_record.status = PaymentStatus.COMPLETED
            from datetime import datetime
            payment_record.completed_at = datetime.utcnow()

            await session.commit()

            card_text = (
                f"✅ *Payment Successful!*\n\n"
                f"Thank you for purchasing with *{stars_amount} ⭐*!\n\n"
                f"🎁 *Your Gift Card*\n"
                f"`{card.code}`\n"
                f"💵 Value: *${card.amount/100:.2f}*\n\n"
                f"Save this code and share it with the recipient."
            )

            keyboard = [
                [
                    InlineKeyboardButton("🎫 Generate Another", callback_data="menu_generate")
                ]
            ]
            from telegram import InlineKeyboardMarkup
            await update.effective_message.reply_text(
                card_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.effective_message.reply_text(
                "❌ Error generating card. Please contact support."
            )


def register(application):
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CallbackQueryHandler(initiate_payment, pattern="^buy_"))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler)
    )