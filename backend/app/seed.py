from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Achievement, Admin, Case, Reward, Skin, Task


def seed_data(db: Session) -> None:
    rewards = [
        ("AK-47 | Slate (Field-Tested)", "AK-47", "Field-Tested", "https://images.unsplash.com/photo-1612287230202-1ff1d85d1bdf?w=600&auto=format&fit=crop&q=80"),
        ("USP-S | Cortex (Minimal Wear)", "USP-S", "Minimal Wear", "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop&q=80"),
        ("AWP | Atheris (Field-Tested)", "AWP", "Field-Tested", "https://images.unsplash.com/photo-1593305841991-05c297ba4575?w=600&auto=format&fit=crop&q=80"),
    ]
    for name, weapon, exterior, image in rewards:
        reward = db.scalar(select(Reward).where(Reward.name == name))
        if reward is None:
            reward = Reward(name=name, weapon=weapon, exterior=exterior, image_url=image, description="Development catalog sample; not a delivery confirmation.")
            db.add(reward)
            db.flush()
        if db.scalar(select(Skin.id).where(Skin.market_name == name)) is None:
            db.add(Skin(market_name=name, weapon=weapon, exterior=exterior, image_url=image, is_development_data=True))
    db.flush()
    cases = [
        ("first-drop", "First Drop", "A guaranteed, published starter skin. One opening per account.", "free", 0),
        ("night-ops", "Night Ops", "A fixed, published reward from our development catalog.", "featured", 1),
        ("field-kit", "Field Kit", "A transparent free case with a predetermined reward.", "classic", 2),
    ]
    for slug, name, description, _image, reward_index in cases:
        if db.scalar(select(Case.id).where(Case.slug == slug)) is None:
            reward = db.scalar(select(Reward).where(Reward.name == rewards[reward_index][0]))
            db.add(Case(
                slug=slug,
                name=name,
                description=description,
                image_url=rewards[reward_index][3],
                price=0,
                published_reward_id=reward.id,
                is_published=True,
                is_free=True,
            ))
    tasks = [
        ("daily-checkin", "Daily check-in", "Claim a small crystal bonus once per UTC day.", "daily", 10),
        ("complete-profile", "Complete your profile", "Set a username to finish your player profile.", "profile", 20),
        ("community", "Join the community", "Community task; reward requires server-side verification.", "social", 15),
    ]
    for slug, title, description, task_type, reward in tasks:
        if db.scalar(select(Task.id).where(Task.slug == slug)) is None:
            db.add(Task(slug=slug, title=title, description=description, task_type=task_type, reward=reward))
    achievements = [
        ("first-case", "First Drop", "Open your first free case.", "crosshair"),
        ("first-task", "Getting Started", "Claim your first verified task reward.", "sparkles"),
        ("collector", "Collector", "Add three items to your inventory.", "layers"),
    ]
    for slug, title, description, icon in achievements:
        if db.scalar(select(Achievement.id).where(Achievement.slug == slug)) is None:
            db.add(Achievement(slug=slug, title=title, description=description, icon=icon))
    if db.scalar(select(Admin.id).where(Admin.username == settings.admin_username)) is None:
        if settings.app_env == "production" and settings.admin_password == "change-this-before-use":
            raise RuntimeError("Set a non-default ADMIN_PASSWORD before production startup")
        db.add(Admin(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
    db.commit()
