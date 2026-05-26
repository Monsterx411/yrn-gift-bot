from datetime import datetime, timedelta
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from .models import (
    User, CardTemplate, GiftCard, Payment,
    CardStatus, PaymentStatus, AdminLog
)
from bot.card_generator import generate_gift_code

import logging
logger = logging.getLogger(__name__)


# ── Seed Default Templates ─────────────────────────────────
DEFAULT_TEMPLATES = [
    {"key": "basic",  "name": "Basic Gift Card",  "description": "$10 Basic Gift Card",  "amount": 1000, "currency": "USD", "color": "#4CAF50", "price_stars": 10},
    {"key": "premium","name": "Premium Gift Card","description": "$50 Premium Gift Card","amount": 5000, "currency": "USD", "color": "#FFD700", "price_stars": 45},
    {"key": "vip",    "name": "VIP Gift Card",     "description": "$100 VIP Gift Card",  "amount": 10000,"currency": "USD", "color": "#9C27B0", "price_stars": 85},
]


async def seed_default_templates(session: AsyncSession) -> None:
    """Insert default templates if the table is empty."""
    result = await session.execute(select(func.count(CardTemplate.id)))
    count = result.scalar()
    if count == 0:
        for tmpl in DEFAULT_TEMPLATES:
            session.add(CardTemplate(**tmpl))
        await session.flush()
        logger.info(f"Seeded {len(DEFAULT_TEMPLATES)} default card templates.")


# ── Users ──────────────────────────────────────────────────
async def get_or_create_user(session: AsyncSession, telegram_id: int, **kwargs) -> User:
    """Get user by telegram_id or create a new one."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=kwargs.get("username"),
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
        )
        session.add(user)
        await session.flush()
        logger.info(f"Created new user: {telegram_id}")
    else:
        # Update info if changed
        update_fields = False
        for field in ("username", "first_name", "last_name"):
            val = kwargs.get(field)
            if val and getattr(user, field) != val:
                setattr(user, field, val)
                update_fields = True
        if update_fields:
            await session.flush()
    return user


async def get_user_by_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def set_admin(session: AsyncSession, telegram_id: int, is_admin: bool = True) -> Optional[User]:
    user = await get_user_by_id(session, telegram_id)
    if user:
        user.is_admin = is_admin
        await session.flush()
    return user


# ── Card Templates ─────────────────────────────────────────
async def get_active_templates(session: AsyncSession) -> List[CardTemplate]:
    result = await session.execute(
        select(CardTemplate).where(CardTemplate.is_active == True)
    )
    return list(result.scalars().all())


async def get_template_by_key(session: AsyncSession, key: str) -> Optional[CardTemplate]:
    result = await session.execute(
        select(CardTemplate).where(CardTemplate.key == key, CardTemplate.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_template_by_id(session: AsyncSession, template_id: int) -> Optional[CardTemplate]:
    result = await session.execute(select(CardTemplate).where(CardTemplate.id == template_id))
    return result.scalar_one_or_none()


async def create_template(session: AsyncSession, data: dict) -> CardTemplate:
    tmpl = CardTemplate(**data)
    session.add(tmpl)
    await session.flush()
    return tmpl


async def update_template(session: AsyncSession, template_id: int, data: dict) -> Optional[CardTemplate]:
    tmpl = await get_template_by_id(session, template_id)
    if tmpl:
        for key, val in data.items():
            if hasattr(tmpl, key):
                setattr(tmpl, key, val)
        await session.flush()
    return tmpl


async def delete_template(session: AsyncSession, template_id: int) -> bool:
    tmpl = await get_template_by_id(session, template_id)
    if tmpl:
        tmpl.is_active = False
        await session.flush()
        return True
    return False


# ── Gift Cards ─────────────────────────────────────────────
async def generate_card(
    session: AsyncSession,
    user_id: int,
    template_key: str,
    metadata: Optional[dict] = None
) -> Optional[GiftCard]:
    """Generate a new gift card for a user."""
    template = await get_template_by_key(session, template_key)
    if not template:
        logger.warning(f"Template '{template_key}' not found or inactive")
        return None

    code = generate_gift_code()

    card = GiftCard(
        code=code,
        user_id=user_id,
        template_id=template.id,
        amount=template.amount,
        currency=template.currency,
        status=CardStatus.ACTIVE,
        metadata_json=metadata or {},
    )
    session.add(card)

    # Update user stats
    user = await get_user_by_id(session, user_id)
    if user:
        user.total_cards_generated += 1

    await session.flush()
    logger.info(f"Generated card {code} for user {user_id}")
    return card


async def get_user_cards(
    session: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0
) -> List[GiftCard]:
    result = await session.execute(
        select(GiftCard)
        .where(GiftCard.user_id == user_id)
        .order_by(GiftCard.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_card_by_code(session: AsyncSession, code: str) -> Optional[GiftCard]:
    result = await session.execute(select(GiftCard).where(GiftCard.code == code))
    return result.scalar_one_or_none()


async def redeem_card(session: AsyncSession, code: str, redeemed_by: str) -> Optional[GiftCard]:
    card = await get_card_by_code(session, code)
    if card and card.status == CardStatus.ACTIVE:
        card.status = CardStatus.REDEEMED
        card.redeemed_by = redeemed_by
        card.redeemed_at = datetime.utcnow()
        await session.flush()
    return card


# ── Payments ───────────────────────────────────────────────
async def create_payment(
    session: AsyncSession,
    user_id: int,
    amount_stars: int,
    payload: str,
    card_id: Optional[int] = None
) -> Payment:
    payment = Payment(
        user_id=user_id,
        amount_stars=amount_stars,
        payload=payload,
        card_id=card_id,
        status=PaymentStatus.PENDING,
    )
    session.add(payment)
    await session.flush()
    return payment


async def complete_payment(
    session: AsyncSession,
    telegram_payment_charge_id: str,
    provider_charge_id: Optional[str] = None
) -> Optional[Payment]:
    result = await session.execute(
        select(Payment).where(Payment.telegram_payment_charge_id == telegram_payment_charge_id)
    )
    payment = result.scalar_one_or_none()
    if payment:
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        if provider_charge_id:
            payment.provider_charge_id = provider_charge_id
        await session.flush()
    return payment


async def get_payment_by_payload(session: AsyncSession, payload: str) -> Optional[Payment]:
    result = await session.execute(select(Payment).where(Payment.payload == payload))
    return result.scalar_one_or_none()


# ── Admin Stats ────────────────────────────────────────────
async def get_dashboard_stats(session: AsyncSession) -> dict:
    total_users = (await session.execute(select(func.count(User.id)))).scalar()
    total_cards = (await session.execute(select(func.count(GiftCard.id)))).scalar()
    active_cards = (
        await session.execute(
            select(func.count(GiftCard.id)).where(GiftCard.status == CardStatus.ACTIVE)
        )
    ).scalar()
    total_payments = (await session.execute(select(func.count(Payment.id)))).scalar()
    total_stars = (
        await session.execute(
            select(func.coalesce(func.sum(Payment.amount_stars), 0))
            .where(Payment.status == PaymentStatus.COMPLETED)
        )
    ).scalar()
    today_cards = (
        await session.execute(
            select(func.count(GiftCard.id))
            .where(GiftCard.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0))
        )
    ).scalar()

    return {
        "total_users": total_users,
        "total_cards": total_cards,
        "active_cards": active_cards,
        "total_payments": total_payments,
        "total_stars_earned": total_stars,
        "cards_generated_today": today_cards,
    }


# ── Admin Log ──────────────────────────────────────────────
async def log_admin_action(session: AsyncSession, admin_id: int, action: str, details: Optional[dict] = None):
    log = AdminLog(admin_id=admin_id, action=action, details=details)
    session.add(log)
    await session.flush()