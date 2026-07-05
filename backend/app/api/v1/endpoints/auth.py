from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.api.request_utils import client_ip
from app.schemas.common import success
from app.schemas.user import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService
from app.services.log_service import LogService

router = APIRouter()


@router.post("/register")
def register(payload: UserRegisterRequest, request: Request, db: DbSession):
    result = AuthService(db).register(payload)
    LogService(db).record(
        user_id=result.user_id,
        action="REGISTER",
        target_type="user_account",
        target_id=result.user_id,
        detail=f"用户 {result.account} 注册账号",
        ip=client_ip(request),
    )
    return success(result)


@router.post("/login")
def login(payload: UserLoginRequest, request: Request, db: DbSession):
    result = AuthService(db).login(payload)
    LogService(db).record(
        user_id=result.user.user_id,
        action="LOGIN",
        target_type="user_account",
        target_id=result.user.user_id,
        detail=f"用户 {result.user.account} 登录系统",
        ip=client_ip(request),
    )
    return success(result)


@router.get("/me")
def me(current_user: CurrentUser):
    return success(AuthService.to_user_dto(current_user))
