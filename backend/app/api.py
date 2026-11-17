from datetime import datetime, timezone
import re
from urllib.parse import parse_qs, parse_qsl, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, validate_telegram_init_data, verify_password
from app.dependencies import current_admin, current_user
from app.models import (
    Achievement, Admin, AuditLog, Case, CaseOpening, ExperienceTransaction, InventoryItem, InventoryStatus,
    Referral, Reward, Skin, Task, User, UserProfile, UserTask, Wallet, WalletTransaction, WithdrawalRequest,
)
from app.schemas import (
    AdminLoginRequest, AdminUserUpdate, CaseCreate, CaseOut, DemoAuthRequest, RewardCreate,
    SkinCreate, TaskCreate, TaskOut, TelegramAuthRequest, SteamURLRequest,
)
from app.services.case_engine import open_free_case
from app.services.steam_provider import steam_delivery_provider

router = APIRouter(prefix="/api")


def _upsert_user(db: Session, telegram_user: dict, referral_code: str | None = None) -> User:
    user = db.scalar(select(User).where(User.telegram_id == int(telegram_user["id"])))
    username = telegram_user.get("username") or telegram_user.get("first_name") or "player"
    if user is None:
        user = User(
            telegram_id=int(telegram_user["id"]),
            username=username[:64],
            first_name=(telegram_user.get("first_name") or "")[:128],
            avatar_url=telegram_user.get("photo_url"),
        )
        db.add(user)
        db.flush()
        db.add_all([UserProfile(user_id=user.id), Wallet(user_id=user.id)])
        if referral_code and referral_code != user.referral_code:
            referrer = db.scalar(select(User).where(User.referral_code == referral_code))
            if referrer and referrer.telegram_id != user.telegram_id:
                user.referred_by_id = referrer.id
                db.add(Referral(referrer_id=referrer.id, referred_user_id=user.id))
    else:
        user.username = username[:64]
        user.first_name = (telegram_user.get("first_name") or "")[:128]
        user.avatar_url = telegram_user.get("photo_url")
    db.commit()
    db.refresh(user)
    return user


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "delivery_enabled": steam_delivery_provider.enabled}


@router.post("/auth/telegram")
def telegram_login(payload: TelegramAuthRequest, db: Session = Depends(get_db)) -> dict:
    user_data = validate_telegram_init_data(payload.init_data)
    params = dict(parse_qsl(payload.init_data))
    user = _upsert_user(db, user_data, params.get("start_param"))
    return {"access_token": create_access_token(str(user.id)), "token_type": "bearer"}


@router.post("/auth/demo")
def demo_login(payload: DemoAuthRequest, db: Session = Depends(get_db)) -> dict:
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Not found")
    import hashlib
    demo_id = int(hashlib.sha256(payload.username.encode()).hexdigest()[:8], 16) + 1
    user = _upsert_user(db, {"id": demo_id, "username": payload.username, "first_name": payload.username})
    return {"access_token": create_access_token(str(user.id)), "token_type": "bearer"}


@router.post("/auth/admin")
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> dict:
    admin = db.scalar(select(Admin).where(Admin.username == payload.username, Admin.is_active.is_(True)))
    if admin is None or admin.role not in {"admin", "superadmin"} or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_access_token(str(admin.id), "admin"), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    inventory_count = db.scalar(select(func.count()).select_from(InventoryItem).where(InventoryItem.user_id == user.id)) or 0
    referral_count = db.scalar(select(func.count()).select_from(Referral).where(Referral.referrer_id == user.id)) or 0
    has_opened_case = db.scalar(select(CaseOpening.id).where(CaseOpening.user_id == user.id).limit(1)) is not None
    has_claimed_task = db.scalar(select(UserTask.id).where(
        UserTask.user_id == user.id, UserTask.status == "completed").limit(1)) is not None
    achievements = [
        {"slug": achievement.slug, "title": achievement.title, "description": achievement.description,
         "icon": achievement.icon,
         "unlocked": (
             has_opened_case if achievement.slug == "first-case"
             else has_claimed_task if achievement.slug == "first-task"
             else inventory_count >= 3 if achievement.slug == "collector"
             else False
         )}
        for achievement in db.scalars(select(Achievement).order_by(Achievement.id))
    ]
    return {
        "id": user.id, "telegram_id": user.telegram_id, "username": user.username,
        "first_name": user.first_name, "avatar_url": user.avatar_url,
        "level": profile.level, "xp": profile.xp, "crystals": wallet.crystals,
        "steam_connected": bool(profile.steam_trade_url), "inventory_count": inventory_count,
        "referral_count": referral_count, "referral_code": user.referral_code,
        "achievements": achievements,
    }


@router.get("/cases", response_model=list[CaseOut])
def cases(db: Session = Depends(get_db), _user: User = Depends(current_user)) -> list[dict]:
    rows = db.execute(select(Case, Reward).join(Reward, Case.published_reward_id == Reward.id)
                      .where(Case.is_published.is_(True)).order_by(Case.id))
    return [{"id": case.id, "slug": case.slug, "name": case.name, "description": case.description,
             "image_url": case.image_url, "price": case.price, "is_free": case.is_free,
             "published_reward_name": reward.name} for case, reward in rows]


@router.post("/cases/{slug}/open")
def open_case(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return open_free_case(db, user.id, slug)


@router.get("/inventory")
def inventory(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(InventoryItem, Skin).join(Skin).where(InventoryItem.user_id == user.id).order_by(InventoryItem.acquired_at.desc()))
    return [
        {"id": item.id, "name": skin.market_name, "weapon": skin.weapon, "image_url": skin.image_url,
         "exterior": skin.exterior, "float_value": skin.float_value, "asset_id": skin.provider_asset_id,
         "status": item.status, "acquired_at": item.acquired_at, "development_data": skin.is_development_data}
        for item, skin in rows
    ]


@router.get("/tasks", response_model=list[TaskOut])
def tasks(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    output = []
    today = datetime.now(timezone.utc).date().isoformat()
    for task in db.scalars(select(Task).where(Task.is_active.is_(True)).order_by(Task.id)):
        user_task = db.scalar(select(UserTask).where(UserTask.user_id == user.id, UserTask.task_id == task.id))
        status = user_task.status if user_task else "pending"
        if task.task_type == "daily":
            status = "completed" if db.scalar(select(WalletTransaction.id).where(
                WalletTransaction.user_id == user.id, WalletTransaction.reason == "task_reward",
                WalletTransaction.reference == f"{task.slug}:{today}",
            )) else "pending"
        output.append({"id": task.id, "slug": task.slug, "title": task.title, "description": task.description,
                       "task_type": task.task_type, "reward": task.reward, "status": status,
                       "verification_status": user_task.verification_status if user_task else "unverified"})
    return output


@router.post("/tasks/{slug}/claim")
def claim_task(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    task = db.scalar(select(Task).where(Task.slug == slug, Task.is_active.is_(True)))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.task_type == "social":
        raise HTTPException(status_code=400, detail="This task requires server-side verification")
    if task.task_type == "profile" and not user.username:
        raise HTTPException(status_code=400, detail="Complete your profile before claiming this reward")
    reference = f"{task.slug}:{datetime.now(timezone.utc).date().isoformat()}" if task.task_type == "daily" else task.slug
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id).with_for_update())
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if db.scalar(select(WalletTransaction.id).where(
        WalletTransaction.user_id == user.id, WalletTransaction.reason == "task_reward",
        WalletTransaction.reference == reference,
    )):
        raise HTTPException(status_code=409, detail="Task reward has already been claimed")
    wallet.crystals += task.reward
    db.add(WalletTransaction(user_id=user.id, amount=task.reward, reason="task_reward", reference=reference))
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id).with_for_update())
    profile.xp += task.reward
    profile.level = profile.xp // 100 + 1
    db.add(ExperienceTransaction(user_id=user.id, amount=task.reward, reason="task_reward"))
    record = db.scalar(select(UserTask).where(UserTask.user_id == user.id, UserTask.task_id == task.id))
    if record is None:
        db.add(UserTask(user_id=user.id, task_id=task.id, status="completed", verification_status="verified", completed_at=datetime.now(timezone.utc)))
    else:
        record.status = "completed"
        record.verification_status = "verified"
        record.completed_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A task reward has already been claimed") from None
    return {"rewarded": task.reward, "crystals": wallet.crystals}


@router.put("/steam")
def save_steam_url(payload: SteamURLRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        parsed = urlparse(payload.trade_url)
    except ValueError:
        raise HTTPException(status_code=422, detail="Enter a valid Steam Trade URL") from None
    query = parse_qs(parsed.query)
    partner = query.get("partner", [""])[0]
    token = query.get("token", [""])[0]
    if (parsed.scheme != "https" or parsed.netloc.lower() not in {"steamcommunity.com", "steamcommunity.com:443"}
            or parsed.path != "/tradeoffer/new/" or not partner.isdigit() or len(partner) > 20
            or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", token) is None):
        raise HTTPException(status_code=422, detail="Enter a valid Steam Trade URL")
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    profile.steam_trade_url = payload.trade_url
    db.commit()
    return {"steam_connected": True}


@router.get("/steam")
def get_steam_url(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    return {"steam_connected": bool(profile.steam_trade_url), "trade_url": profile.steam_trade_url}


@router.get("/withdrawals")
def withdrawals(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(WithdrawalRequest, InventoryItem, Skin)
                      .join(InventoryItem, WithdrawalRequest.inventory_item_id == InventoryItem.id)
                      .join(Skin, InventoryItem.skin_id == Skin.id)
                      .where(WithdrawalRequest.user_id == user.id).order_by(WithdrawalRequest.created_at.desc()))
    return [{"id": req.id, "status": req.status, "created_at": req.created_at, "skin": skin.market_name}
            for req, _item, skin in rows]


@router.post("/withdrawals/{item_id}")
def request_withdrawal(item_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(WithdrawalRequest.id).where(WithdrawalRequest.inventory_item_id == item_id)):
        raise HTTPException(status_code=409, detail="A withdrawal request already exists for this item")
    item = db.scalar(select(InventoryItem).where(InventoryItem.id == item_id, InventoryItem.user_id == user.id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.status != InventoryStatus.AVAILABLE.value:
        raise HTTPException(status_code=409, detail="This item is not available for withdrawal")
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if not profile.steam_trade_url:
        raise HTTPException(status_code=400, detail="Add a valid Steam Trade URL first")
    item.status = InventoryStatus.WITHDRAWAL_REQUESTED.value
    request = WithdrawalRequest(user_id=user.id, inventory_item_id=item.id)
    db.add(request)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A withdrawal request already exists for this item") from None
    return {"id": request.id, "status": request.status, "delivery_enabled": steam_delivery_provider.enabled}


@router.get("/referrals")
def referrals(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    referred = db.execute(select(User.username, Referral.created_at, Referral.status)
                          .join(Referral, Referral.referred_user_id == User.id)
                          .where(Referral.referrer_id == user.id).order_by(Referral.created_at.desc())).all()
    link = f"https://t.me/{settings.telegram_bot_username}?start={user.referral_code}" if settings.telegram_bot_username else None
    return {"code": user.referral_code, "link": link, "count": len(referred),
            "users": [{"username": name, "created_at": created, "status": status} for name, created, status in referred]}


@router.get("/leaderboard")
def leaderboard(period: str = Query("all-time", pattern="^(weekly|monthly|all-time)$"),
                _user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    query = select(User.id, User.username, User.avatar_url, UserProfile.level, UserProfile.xp).join(
        UserProfile, UserProfile.user_id == User.id)
    if period == "all-time":
        query = query.order_by(UserProfile.xp.desc())
    else:
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(days=7 if period == "weekly" else 30)
        recent_xp = (select(ExperienceTransaction.user_id, func.sum(ExperienceTransaction.amount).label("points"))
                     .where(ExperienceTransaction.created_at >= since)
                     .group_by(ExperienceTransaction.user_id).subquery())
        query = (select(User.id, User.username, User.avatar_url, UserProfile.level,
                        func.coalesce(recent_xp.c.points, 0).label("points"))
                 .join(UserProfile, UserProfile.user_id == User.id)
                 .outerjoin(recent_xp, recent_xp.c.user_id == User.id)
                 .order_by(func.coalesce(recent_xp.c.points, 0).desc()))
    rows = db.execute(query.limit(50)).all()
    return [{"rank": rank, "user_id": uid, "username": username, "avatar_url": avatar,
             "level": level, "points": xp} for rank, (uid, username, avatar, level, xp) in enumerate(rows, 1)]


@router.get("/transactions")
def transactions(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "amount": row.amount, "reason": row.reason, "created_at": row.created_at}
            for row in db.scalars(select(WalletTransaction).where(WalletTransaction.user_id == user.id)
                                  .order_by(WalletTransaction.created_at.desc()).limit(100))]


@router.get("/admin/overview")
def admin_overview(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> dict:
    return {
        "users": db.scalar(select(func.count()).select_from(User)) or 0,
        "cases": db.scalar(select(func.count()).select_from(Case)) or 0,
        "withdrawals_pending": db.scalar(select(func.count()).select_from(WithdrawalRequest)
                                         .where(WithdrawalRequest.status == "requested")) or 0,
        "transactions": db.scalar(select(func.count()).select_from(WalletTransaction)) or 0,
    }


@router.get("/admin/users")
def admin_users(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": user.id, "telegram_id": user.telegram_id, "username": user.username,
             "is_active": user.is_active, "created_at": user.created_at}
            for user in db.scalars(select(User).order_by(User.id.desc()).limit(100))]


@router.patch("/admin/users/{user_id}")
def admin_update_user(user_id: int, payload: AdminUserUpdate, admin: Admin = Depends(current_admin),
                      db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = payload.is_active
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="user.account_status",
                    target=str(user_id), details=f"is_active={payload.is_active}"))
    db.commit()
    return {"id": user.id, "is_active": payload.is_active}


@router.post("/admin/tasks")
def admin_create_task(payload: TaskCreate, admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(Task.id).where(Task.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Task slug already exists")
    task = Task(**payload.model_dump())
    db.add(task)
    db.flush()
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="task.create", target=str(task.id), details=task.slug))
    db.commit()
    return {"id": task.id, "slug": task.slug}


@router.get("/admin/tasks")
def admin_tasks(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "slug": row.slug, "title": row.title, "task_type": row.task_type,
             "reward": row.reward, "is_active": row.is_active}
            for row in db.scalars(select(Task).order_by(Task.id))]


@router.get("/admin/cases")
def admin_cases(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Case, Reward).outerjoin(Reward, Case.published_reward_id == Reward.id))
    return [{"id": case.id, "slug": case.slug, "name": case.name, "description": case.description,
             "reward": reward.name if reward else None, "published": case.is_published,
             "free": case.is_free} for case, reward in rows]


@router.post("/admin/cases")
def admin_create_case(payload: CaseCreate, admin: Admin = Depends(current_admin),
                      db: Session = Depends(get_db)) -> dict:
    reward = db.get(Reward, payload.published_reward_id)
    if reward is None or not reward.is_published:
        raise HTTPException(status_code=400, detail="Choose a published reward")
    if db.scalar(select(Case.id).where(Case.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Case slug already exists")
    case = Case(**payload.model_dump(), price=0, is_free=True)
    db.add(case)
    db.flush()
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="case.create",
                    target=str(case.id), details=case.slug))
    db.commit()
    return {"id": case.id, "slug": case.slug}


@router.get("/admin/rewards")
def admin_rewards(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "name": row.name, "weapon": row.weapon, "exterior": row.exterior,
             "published": row.is_published} for row in db.scalars(select(Reward).order_by(Reward.id))]


@router.post("/admin/rewards")
def admin_create_reward(payload: RewardCreate, admin: Admin = Depends(current_admin),
                        db: Session = Depends(get_db)) -> dict:
    reward = Reward(**payload.model_dump())
    db.add(reward)
    db.flush()
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="reward.create",
                    target=str(reward.id), details=reward.name))
    db.commit()
    return {"id": reward.id, "name": reward.name}


@router.get("/admin/skins")
def admin_skins(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "market_name": row.market_name, "weapon": row.weapon,
             "development_data": row.is_development_data}
            for row in db.scalars(select(Skin).order_by(Skin.id))]


@router.post("/admin/skins")
def admin_create_skin(payload: SkinCreate, admin: Admin = Depends(current_admin),
                      db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(Skin.id).where(Skin.market_name == payload.market_name)):
        raise HTTPException(status_code=409, detail="Skin already exists")
    skin = Skin(**payload.model_dump(), is_development_data=False)
    db.add(skin)
    db.flush()
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="skin.create",
                    target=str(skin.id), details=skin.market_name))
    db.commit()
    return {"id": skin.id, "market_name": skin.market_name}


@router.get("/admin/inventory")
def admin_inventory(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(InventoryItem, User, Skin).join(User, InventoryItem.user_id == User.id)
                      .join(Skin, InventoryItem.skin_id == Skin.id)
                      .order_by(InventoryItem.acquired_at.desc()).limit(200))
    return [{"id": item.id, "username": user.username, "skin": skin.market_name, "status": item.status,
             "acquired_at": item.acquired_at, "asset_id": skin.provider_asset_id}
            for item, user, skin in rows]


@router.get("/admin/referrals")
def admin_referrals(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"total": db.scalar(select(func.count()).select_from(Referral)) or 0,
             "pending": db.scalar(select(func.count()).select_from(Referral).where(Referral.status == "pending")) or 0}]


@router.get("/admin/transactions")
def admin_transactions(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(WalletTransaction, User).join(User, WalletTransaction.user_id == User.id)
                      .order_by(WalletTransaction.created_at.desc()).limit(200))
    return [{"id": transaction.id, "username": user.username, "amount": transaction.amount,
             "reason": transaction.reason, "created_at": transaction.created_at}
            for transaction, user in rows]


@router.get("/admin/withdrawals")
def admin_withdrawals(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(WithdrawalRequest, User, InventoryItem, Skin)
                      .join(User, WithdrawalRequest.user_id == User.id)
                      .join(InventoryItem, WithdrawalRequest.inventory_item_id == InventoryItem.id)
                      .join(Skin, InventoryItem.skin_id == Skin.id)
                      .order_by(WithdrawalRequest.created_at.desc()).limit(100))
    return [{"id": request.id, "username": user.username, "skin": skin.market_name,
             "status": request.status, "created_at": request.created_at}
            for request, user, _item, skin in rows]


@router.patch("/admin/withdrawals/{request_id}")
def admin_update_withdrawal(request_id: int, status: str, admin: Admin = Depends(current_admin),
                            db: Session = Depends(get_db)) -> dict:
    if status != "cancelled":
        raise HTTPException(status_code=422, detail="Delivery status can only be updated by an authorized provider")
    request = db.get(WithdrawalRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    if request.status != "requested":
        raise HTTPException(status_code=409, detail="Only requested withdrawals can be updated")
    request.status = status
    item = db.get(InventoryItem, request.inventory_item_id)
    item.status = InventoryStatus.PROCESSING.value if status == "processing" else InventoryStatus.CANCELLED.value
    db.add(AuditLog(admin_id=admin.id, actor=admin.username, action="withdrawal.update",
                    target=str(request.id), details=status))
    db.commit()
    return {"id": request.id, "status": request.status}


@router.get("/admin/audit-logs")
def admin_audit_logs(_admin: Admin = Depends(current_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": row.id, "actor": row.actor, "action": row.action, "target": row.target,
             "details": row.details, "created_at": row.created_at}
            for row in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200))]
