from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NOT_FOUND
from app.models import UserAccount
from app.schemas.user import UserDTO


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def list_users(
        self,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[UserDTO], int]:
        query = select(UserAccount)
        count_query = select(func.count()).select_from(UserAccount)
        if keyword:
            condition = or_(
                UserAccount.account.like(f"%{keyword}%"),
                UserAccount.email.like(f"%{keyword}%"),
            )
            query = query.where(condition)
            count_query = count_query.where(condition)
        if status:
            query = query.where(UserAccount.status == status)
            count_query = count_query.where(UserAccount.status == status)

        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(UserAccount.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [self._to_dto(row) for row in rows], total

    def set_user_status(self, user_id: int, status: str) -> UserDTO:
        user = self.db.get(UserAccount, user_id)
        if not user:
            raise AppException(NOT_FOUND, "User not found", 404)
        user.status = status
        self.db.commit()
        self.db.refresh(user)
        return self._to_dto(user)

    def _to_dto(self, user: UserAccount) -> UserDTO:
        return UserDTO(
            user_id=user.id,
            account=user.account,
            email=user.email,
            role=user.role,
            status=user.status,
            register_time=user.register_time,
            last_login_time=user.last_login_time,
        )
