from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from bot.config import config
from database.models import CardTemplate
from typing import List, Optional


def webapp_button(text: str = "🎁 Open Gift Card Generator") -> InlineKeyboardButton:
    return InlineKeyboardButton(text, web_app=WebAppInfo(url=config.WEBAPP_URL))


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu with inline buttons."""
    keyboard = [
        [InlineKeyboardButton("🎫 Generate Card", callback_data="menu_generate")],
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance")],
        [InlineKeyboardButton("📋 History", callback_data="menu_history")],
        [webapp_button()],
    ]
    return InlineKeyboardMarkup(keyboard)


def card_template_keyboard(templates: List[CardTemplate]) -> InlineKeyboardMarkup:
    """Build keyboard from active templates."""
    keyboard = []
    for tmpl in templates:
        btn_text = f"{tmpl.name} — ${tmpl.amount/100:.2f}"
        if tmpl.price_stars > 0:
            btn_text += f" ({tmpl.price_stars}⭐)"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"gen_{tmpl.key}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu_back")])
    return InlineKeyboardMarkup(keyboard)


def back_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="menu_back")]]
    return InlineKeyboardMarkup(keyboard)


def admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("📝 Templates", callback_data="admin_templates")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Exit Admin", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def payment_keyboard(amount_stars: int, payload: str) -> InlineKeyboardMarkup:
    """Buy button with Telegram Stars."""
    keyboard = [[
        InlineKeyboardButton(
            f"💳 Pay {amount_stars} ⭐",
            pay=True
        )
    ]]
    return InlineKeyboardMarkup(keyboard)