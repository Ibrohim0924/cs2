import enum
import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InventoryStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    WITHDRAWAL_REQUESTED = "withdrawal_requested"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class WithdrawalStatus(str, enum.Enum):
    REQUESTED = "requested"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64), default="player")
    first_name: Mapped[str] = mapped_column(String(128), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, default=lambda: secrets.token_urlsafe(8)[:10])
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    steam_trade_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user: Mapped[User] = relationship(back_populates="profile")


class ExperienceTransaction(Base):
    __tablename__ = "experience_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    crystals: Mapped[int] = mapped_column(Integer, default=0)
    user: Mapped[User] = relationship(back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "reason", "reference", name="uq_wallet_transaction_reference"),)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(1024), default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    published_reward_id: Mapped[int | None] = mapped_column(ForeignKey("rewards.id"), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    # Free-case mode is the only supported mode; no paid or random openings.
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)


class CaseOpening(Base):
    __tablename__ = "case_openings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "case_id", name="uq_user_case_opening"),)


class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(String(1024), default="")
    weapon: Mapped[str] = mapped_column(String(80), default="")
    exterior: Mapped[str] = mapped_column(String(80), default="")
    float_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class Skin(Base):
    __tablename__ = "skins"
    id: Mapped[int] = mapped_column(primary_key=True)
    market_name: Mapped[str] = mapped_column(String(180), unique=True)
    weapon: Mapped[str] = mapped_column(String(80))
    image_url: Mapped[str] = mapped_column(String(1024), default="")
    exterior: Mapped[str] = mapped_column(String(80), default="")
    float_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_asset_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_development_data: Mapped[bool] = mapped_column(Boolean, default=True)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skin_id: Mapped[int] = mapped_column(ForeignKey("skins.id"))
    status: Mapped[str] = mapped_column(String(32), default=InventoryStatus.AVAILABLE.value)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(64), default="case")
    skin: Mapped[Skin] = relationship()


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[str] = mapped_column(String(32), default="daily")
    reward: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserTask(Base):
    __tablename__ = "user_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    task: Mapped[Task] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_user_task"),)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(64), default="award")


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"))
    status: Mapped[str] = mapped_column(String(32), default=WithdrawalStatus.REQUESTED.value)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("inventory_item_id", name="uq_withdrawal_inventory_item"),)


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admins.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(160))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


Index("ix_wallet_transactions_user_created", WalletTransaction.user_id, WalletTransaction.created_at)
