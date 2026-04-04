"""
auth.py
FastAPI dependencies for authentication and authorization.
Uses JWTAuthService via the AuthServiceBase interface —
swapping auth implementation requires only changing the import.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User, RoleEnum
from services.jwt_auth_service import jwt_auth_service

bearer_scheme = HTTPBearer()

# Re-export service methods for convenience in routes
hash_password    = jwt_auth_service.hash_password
verify_password  = jwt_auth_service.verify_password
create_access_token  = jwt_auth_service.create_access_token
create_refresh_token = jwt_auth_service.create_refresh_token
decode_token         = jwt_auth_service.decode_token


# ── Current User dependency ────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user.")
    return current_user


# ── RBAC ───────────────────────────────────────────────────────────────────────

def require_role(*roles: RoleEnum):
    """
    Dependency factory for role-based access control.
    Usage: @router.get("/admin", dependencies=[Depends(require_admin)])
    """
    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user
    return checker


require_admin   = require_role(RoleEnum.admin)
require_analyst = require_role(RoleEnum.admin, RoleEnum.analyst)
require_viewer  = require_role(RoleEnum.admin, RoleEnum.analyst, RoleEnum.viewer)