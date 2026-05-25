from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.models import User, GiftCard, Payment, CardTemplate, CardStatus, PaymentStatus


async def get_user_stats(session: AsyncSession, user_id: int) -> dict:
    """Get detailed stats for a specific user."""
    user = await session.get(User, user_id)
    if not user:
        return {}

    total_cards = await session.scalar(
        select(func.count(GiftCard.id)).where(GiftCard.user_id == user_id)
    )
    active_cards = await session.scalar(
        select(func.count(GiftCard.id)).where(
            GiftCard.user_id == user_id,
            GiftCard.status == CardStatus.ACTIVE
        )
    )
    total_spent = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.COMPLETED
        )
    )
    recent_cards = await session.scalar(
        select(func.count(GiftCard.id)).where(
            GiftCard.user_id == user_id,
            GiftCard.created_at >= datetime.utcnow() - timedelta(days=7)
        )
    )

    return {
        "total_cards": total_cards or 0,
        "active_cards": active_cards or 0,
        "total_spent_stars": total_spent or 0,
        "cards_this_week": recent_cards or 0,
    }


def format_amount(amount_cents: int, currency: str = "USD") -> str:
    """Format amount from cents to display string."""
    if currency == "XTR":
        return f"{amount_cents} ⭐"
    return f"${amount_cents / 100:.2f}"