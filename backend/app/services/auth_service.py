from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, CONFLICT, UNAUTHORIZED
from app.core.security import create_access_token, hash_password, verify_password
from app.models import UserAccount
from app.schemas.user import LoginResponse, UserDTO, UserLoginRequest, UserRegisterRequest


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: UserRegisterRequest) -> UserDTO:
        exists = self.db.scalar(
            select(UserAccount).where(
                or_(
                    UserAccount.account == payload.account,
                    UserAccount.email == payload.email,
                )
            )
        )
        if exists:
            raise AppException(CONFLICT, "Account or email already exists", 409)

        user = UserAccount(
            account=payload.account,
            email=payload.email,
            password_hash=hash_password(payload.password),
            status="ACTIVE",
            role="USER",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self.to_user_dto(user)

    def login(self, payload: UserLoginRequest) -> LoginResponse:
        user = self.db.scalar(
            select(UserAccount).where(UserAccount.account == payload.account)
        )
        if not user or user.status != "ACTIVE":
            raise AppException(UNAUTHORIZED, "Invalid account or password", 401)
        if not verify_password(payload.password, user.password_hash):
            raise AppException(UNAUTHORIZED, "Invalid account or password", 401)

        user.last_login_time = datetime.now()
        self.db.commit()
        self.db.refresh(user)
        token = create_access_token(str(user.id), {"role": user.role})
        return LoginResponse(token=token, user=self.to_user_dto(user))

    @staticmethod
    def to_user_dto(user: UserAccount) -> UserDTO:
        return UserDTO(
            user_id=user.id,
            account=user.account,
            email=user.email,
            role=user.role,
            status=user.status,
            register_time=user.register_time,
            last_login_time=user.last_login_time,
        )
