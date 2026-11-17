from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Admin, User

bearer = HTTPBearer(auto_error=False)


def current_claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_access_token(credentials.credentials)


def current_user(claims: dict = Depends(current_claims), db: Session = Depends(get_db)) -> User:
    if claims.get("role") != "user":
        raise HTTPException(status_code=403, detail="User session required")
    user = db.query(User).filter(User.id == int(claims["sub"])).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User account not found")
    return user


def current_admin(claims: dict = Depends(current_claims), db: Session = Depends(get_db)) -> Admin:
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    admin = db.query(Admin).filter(
        Admin.id == int(claims["sub"]),
        Admin.is_active.is_(True),
        Admin.role.in_(("admin", "superadmin")),
    ).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Administrator account not found")
    return admin
