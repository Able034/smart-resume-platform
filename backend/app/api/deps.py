from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException, FORBIDDEN, UNAUTHORIZED
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import UserAccount

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> UserAccount:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AppException(UNAUTHORIZED, "Invalid token subject", 401)
    user = db.get(UserAccount, int(user_id))
    if not user or user.status != "ACTIVE":
        raise AppException(UNAUTHORIZED, "User is not active", 401)
    return user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> UserAccount:
    if current_user.role != "ADMIN":
        raise AppException(FORBIDDEN, "Admin permission required", 403)
    return current_user


CurrentAdmin = Annotated[UserAccount, Depends(get_current_admin)]
