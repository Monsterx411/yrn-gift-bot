from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Enum as SAEnum, JSON, BigInteger
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from typing import Optional, List
import enum


class Base(DeclarativeBase):
    pass


class CardType(str, enum.Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


class CardStatus(str, enum.Enum):
    ACTIVE = "active"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


# ── Users ──────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    balance_stars: Mapped[int] = mapped_column(Integer, default=0)
    total_cards_generated: Mapped[int] = mapped_column(Integer, default=0)
    total_spent_stars: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cards: Mapped[List["GiftCard"]] = relationship("GiftCard", back_populates="user")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.telegram_id} ({self.username})>"


# ── Gift Card Templates ────────────────────────────────────
class CardTemplate(Base):
    __tablename__ = "card_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # e.g. "premium"
    name: Mapped[str] = mapped_column(String(128), nullable=False)              # e.g. "Premium Gift Card"
    description: Mapped[str] = mapped_column(Text, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)                # Value in cents / smallest unit
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    color: Mapped[str] = mapped_column(String(16), default="#4CAF50")
    price_stars: Mapped[int] = mapped_column(Integer, default=0)               # Cost in Telegram Stars (XTR)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cards: Mapped[List["GiftCard"]] = relationship("GiftCard", back_populates="template")

    def __repr__(self) -> str:
        return f"<CardTemplate {self.key}: ${self.amount}>"


# ── Gift Cards (Generated) ─────────────────────────────────
class GiftCard(Base):
    __tablename__ = "gift_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("card_templates.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[CardStatus] = mapped_column(SAEnum(CardStatus), default=CardStatus.ACTIVE)
    redeemed_by: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cards")
    template: Mapped["CardTemplate"] = relationship("CardTemplate", back_populates="cards")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="card", uselist=False)

    def __repr__(self) -> str:
        return f"<GiftCard {self.code} | ${self.amount}>"


# ── Payments (Telegram Stars / XTR) ────────────────────────
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_payment_charge_id: Mapped[Optional[str]] = mapped_column(String(256), unique=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    card_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("gift_cards.id"), nullable=True)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)        # Amount in Telegram Stars
    currency: Mapped[str] = mapped_column(String(8), default="XTR")
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payload: Mapped[str] = mapped_column(String(256), nullable=False)         # Invoice payload
    provider_charge_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    card: Mapped[Optional["GiftCard"]] = relationship("GiftCard", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment {self.telegram_payment_charge_id} | {self.amount_stars} ⭐>"


# ── Admin Log ──────────────────────────────────────────────
class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)