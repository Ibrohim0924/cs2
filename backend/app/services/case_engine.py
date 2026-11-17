from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Case, CaseOpening, InventoryItem, InventoryStatus, Reward, Skin


def open_free_case(db: Session, user_id: int, case_slug: str) -> dict:
    case = db.scalar(select(Case).where(Case.slug == case_slug, Case.is_published.is_(True)))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.is_free or case.price != 0:
        raise HTTPException(status_code=400, detail="Only free cases are supported")
    if db.scalar(select(CaseOpening.id).where(CaseOpening.user_id == user_id, CaseOpening.case_id == case.id)):
        raise HTTPException(status_code=409, detail="This free case has already been opened")
    if case.published_reward_id is None:
        raise HTTPException(status_code=503, detail="Case reward is not configured")
    reward = db.get(Reward, case.published_reward_id)
    if reward is None or not reward.is_published:
        raise HTTPException(status_code=503, detail="Published case reward is unavailable")

    skin = db.scalar(select(Skin).where(Skin.market_name == reward.name))
    if skin is None:
        skin = Skin(
            market_name=reward.name,
            weapon=reward.weapon or "Unknown",
            image_url=reward.image_url,
            exterior=reward.exterior,
            float_value=reward.float_value,
            is_development_data=True,
        )
        db.add(skin)
        db.flush()
    item = InventoryItem(user_id=user_id, skin_id=skin.id, source=f"case:{case.slug}")
    db.add(item)
    db.flush()
    db.add(CaseOpening(user_id=user_id, case_id=case.id, inventory_item_id=item.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This free case has already been opened") from None
    return {"case": case.name, "reward": reward.name, "inventory_item_id": item.id}
