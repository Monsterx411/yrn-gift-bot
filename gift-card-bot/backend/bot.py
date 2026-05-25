import asyncio
import json
import logging
import uuid
import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    WebAppInfo, BotCommand, KeyboardButton, ReplyKeyboardMarkup
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# --- CONFIG ---
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
WEBAPP_URL = "https://your-domain.com/webapp"  # HTTPS required
SECRET_KEY = "your-secret-key-for-hmac"  # used to validate WebApp init data

# --- SETUP ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple in-memory store (replace with DB for production)
# Stores: user_id -> { balance, cards_generated, generated_cards }
user_store = {}

# Template gift cards (admin configurable)
GIFT_TEMPLATES = {
    "premium": {
        "name": "Premium Gift Card",
        "amount": 50,
        "currency": "USD",
        "color": "#FFD700",
        "description": "$50 Premium Gift Card"
    },
    "basic": {
        "name": "Basic Gift Card",
        "amount": 10,
        "currency": "USD",
        "color": "#4CAF50",
        "description": "$10 Basic Gift Card"
    },
    "vip": {
        "name": "VIP Gift Card",
        "amount": 100,
        "currency": "USD",
        "color": "#9C27B0",
        "description": "$100 VIP Gift Card"
    }
}


def generate_gift_code() -> str:
    """Generate a unique gift card code: XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    groups = []
    for _ in range(4):
        group = ''.join(secrets.choice(chars) for _ in range(4))
        groups.append(group)
    return '-'.join(groups)


def validate_webapp_init(init_data: str) -> Optional[dict]:
    """
    Validate Telegram WebApp init data using HMAC-SHA256.
    Returns parsed data dict if valid, None otherwise.
    """
    try:
        # Parse query string
        parsed_data = {}
        for item in init_data.split('&'):
            key, value = item.split('=', 1)
            from urllib.parse import unquote
            parsed_data[key] = unquote(value)

        # Verify hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None

        # Create data check string
        data_check_items = sorted(
            [f"{k}={v}" for k, v in parsed_data.items()],
            key=lambda x: x.split('=')[0]
        )
        data_check_string = '\n'.join(data_check_items)

        # Compute HMAC
        secret_key = hmac.new(
            b"WebAppData",
            SECRET_KEY.encode(),
            hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if expected_hash != received_hash:
            logger.warning("WebApp init data validation failed")
            return None

        return parsed_data
    except Exception as e:
        logger.error(f"WebApp validation error: {e}")
        return None


def get_user(user_id: int) -> dict:
    """Get or create user record."""
    if user_id not in user_store:
        user_store[user_id] = {
            "balance": 0,
            "cards_generated": 0,
            "generated_cards": [],
            "created_at": datetime.utcnow().isoformat()
        }
    return user_store[user_id]


# --- BOT COMMANDS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    get_user(user.id)

    text = (
        f"🎁 *Welcome to Gift Card Generator, {user.first_name}!*\n\n"
        f"I help you generate gift card codes for various services.\n\n"
        f"*Commands:*\n"
        f"`/cards` - Generate a new gift card\n"
        f"`/balance` - Check your balance/stats\n"
        f"`/history` - View your generated cards\n"
        f"`/app` - Open the WebApp\n\n"
        f"Click the button below to open the WebApp and generate cards visually!"
    )

    # Menu button that opens the WebApp
    keyboard = [[
        InlineKeyboardButton(
            "🎁 Open Gift Card Generator",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


async def cards_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show gift card options to generate."""
    keyboard = []
    for key, template in GIFT_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{template['name']} — ${template['amount']}",
                callback_data=f"gen_{key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "🎨 Open WebApp",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a gift card type to generate:",
        reply_markup=reply_markup
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's balance and stats."""
    user = get_user(update.effective_user.id)
    text = (
        f"📊 *Your Stats*\n\n"
        f"💰 Balance: `${user['balance']}`\n"
        f"🎫 Cards Generated: `{user['cards_generated']}`\n"
        f"📅 Member since: `{user['created_at'][:10]}`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show history of generated cards."""
    user = get_user(update.effective_user.id)
    cards = user["generated_cards"][-10:]  # last 10

    if not cards:
        await update.message.reply_text("No cards generated yet. Use /cards to start!")
        return

    text = "*📋 Last 10 Generated Cards*\n\n"
    for card in reversed(cards):
        text += (
            f"`{card['code']}` — "
            f"*{card['type']}* — "
            f"${card['amount']} "
            f"({card['created_at'][:16]})\n"
        )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the WebApp directly."""
    keyboard = [[
        InlineKeyboardButton(
            "🚀 Open Gift Card Generator",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Click below to open the WebApp:",
        reply_markup=reply_markup
    )


# --- CALLBACK HANDLERS ---

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for card generation."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("gen_"):
        card_type = data[4:]
        template = GIFT_TEMPLATES.get(card_type)

        if not template:
            await query.edit_message_text("Invalid card type.")
            return

        # Generate the card
        code = generate_gift_code()
        user = get_user(update.effective_user.id)
        user["cards_generated"] += 1
        user["balance"] += template["amount"]
        user["generated_cards"].append({
            "code": code,
            "type": template["name"],
            "amount": template["amount"],
            "created_at": datetime.utcnow().isoformat()
        })

        # Send the generated card
        text = (
            f"✅ *Gift Card Generated!*\n\n"
            f"┌─────────────────────┐\n"
            f"│  🎁 *{template['name']}*    │\n"
            f"│                     │\n"
            f"│  `{code}`     │\n"
            f"│                     │\n"
            f"│  *${template['amount']}*                │\n"
            f"└─────────────────────┘\n\n"
            f"📋 *Code:* `{code}`\n"
            f"💵 *Value:* `${template['amount']}`\n"
            f"📌 *Use the code above at checkout!*"
        )

        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle data received from the WebApp (via keyboard button send)."""
    web_app_data = update.effective_message.web_app_data
    if not web_app_data:
        return

    try:
        data = json.loads(web_app_data.data)
        action = data.get("action")

        if action == "generate_card":
            card_type = data.get("card_type", "basic")
            template = GIFT_TEMPLATES.get(card_type, GIFT_TEMPLATES["basic"])

            code = generate_gift_code()
            user = get_user(update.effective_user.id)
            user["cards_generated"] += 1
            user["balance"] += template["amount"]
            user["generated_cards"].append({
                "code": code,
                "type": template["name"],
                "amount": template["amount"],
                "created_at": datetime.utcnow().isoformat()
            })

            await update.effective_message.reply_text(
                f"✅ *Card Generated via WebApp!*\n\n"
                f"🎁 *{template['name']}*\n"
                f"`{code}`\n"
                f"💵 *${template['amount']}*",
                parse_mode=ParseMode.MARKDOWN
            )

    except json.JSONDecodeError:
        logger.error("Invalid JSON from WebApp")


async def post_init(application: Application) -> None:
    """Set bot commands and menu button after initialization."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("cards", "Generate a gift card"),
        BotCommand("balance", "Check your balance"),
        BotCommand("history", "View generated cards"),
        BotCommand("app", "Open WebApp"),
    ]
    await application.bot.set_my_commands(commands)

    # Set the menu button to open the WebApp
    await application.bot.set_chat_menu_button(
        menu_button=telegram.MenuButtonWebApp(
            text="🎁 Gift Cards",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cards", cards_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("app", app_command))

    # Callback handler (inline buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))

    # WebApp data handler
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # Start polling
    logger.info("Bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Fix import for menu button
    import telegram
    main()