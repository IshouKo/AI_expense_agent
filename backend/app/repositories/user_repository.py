from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User


def get_or_create_default_user(db: Session) -> User:
    user = db.query(User).order_by(User.id.asc()).first()
    if user:
        return user

    settings = get_settings()
    user = User(
        name=settings.default_user_name,
        default_currency=settings.default_currency,
        timezone=settings.timezone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
