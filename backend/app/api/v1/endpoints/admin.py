from fastapi import APIRouter

from app.api.deps import CurrentAdmin, DbSession
from app.schemas.common import PageData, success
from app.services.admin_service import AdminService

router = APIRouter()


@router.get("/users")
def list_users(
    current_admin: CurrentAdmin,
    db: DbSession,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    pageSize: int = 10,
):
    items, total = AdminService(db).list_users(
        keyword=keyword, status=status, page=page, page_size=pageSize
    )
    return success(PageData(items=items, page=page, page_size=pageSize, total=total))


@router.patch("/users/{user_id}/disable")
def disable_user(user_id: int, current_admin: CurrentAdmin, db: DbSession):
    return success(AdminService(db).set_user_status(user_id, "DISABLED"))


@router.patch("/users/{user_id}/enable")
def enable_user(user_id: int, current_admin: CurrentAdmin, db: DbSession):
    return success(AdminService(db).set_user_status(user_id, "ACTIVE"))
