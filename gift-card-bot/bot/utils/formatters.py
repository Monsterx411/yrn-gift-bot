from database.models import GiftCard, User, CardTemplate
from typing import List


def format_card_display(card: GiftCard) -> str:
    """Format a single gift card for display in Telegram."""
    return (
        f"┌─────────────────────┐\n"
        f"│  🎁 *Gift Card*         │\n"
        f"│                      │\n"
        f"│  `{card.code}`   │\n"
        f"│                      │\n"
        f"│  *${card.amount/100:.2f}*                │\n"
        f"│  *{card.status.value.upper()}*               │\n"
        f"└─────────────────────┘"
    )


def format_card_list(cards: List[GiftCard]) -> str:
    """Format a list of cards for history display."""
    if not cards:
        return "No cards found."

    lines = []
    for i, card in enumerate(cards, 1):
        status_icon = {
            "active": "✅",
            "redeemed": "♻️",
            "expired": "⏰",
            "revoked": "🚫",
        }.get(card.status.value, "❓")
        lines.append(
            f"{i}. {status_icon} `{card.code}` — "
            f"*${card.amount/100:.2f}* — "
            f"*{card.status.value}* — "
            f"_{card.created_at.strftime('%Y-%m-%d %H:%M')}_"
        )
    return "\n".join(lines)


def format_user_profile(user: User, stats: dict) -> str:
    """Format user profile with stats."""
    return (
        f"👤 *User Profile*\n\n"
        f"ID: `{user.telegram_id}`\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Name: {user.first_name or ''} {user.last_name or ''}\n"
        f"Admin: {'✅ Yes' if user.is_admin else '❌ No'}\n\n"
        f"📊 *Stats*\n"
        f"🎫 Cards: {stats.get('total_cards', 0)}\n"
        f"✅ Active: {stats.get('active_cards', 0)}\n"
        f"⭐ Stars Spent: {stats.get('total_spent_stars', 0)}\n"
        f"📅 This Week: {stats.get('cards_this_week', 0)}"
    )


def format_admin_dashboard(stats: dict) -> str:
    """Format admin dashboard stats."""
    return (
        f"📊 *Admin Dashboard*\n\n"
        f"👥 Total Users: `{stats['total_users']}`\n"
        f"🎫 Total Cards: `{stats['total_cards']}`\n"
        f"✅ Active Cards: `{stats['active_cards']}`\n"
        f"💳 Total Payments: `{stats['total_payments']}`\n"
        f"⭐ Stars Earned: `{stats['total_stars_earned']}`\n"
        f"📅 Today's Cards: `{stats['cards_generated_today']}`"
    )