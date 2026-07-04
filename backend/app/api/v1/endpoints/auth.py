from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import success
from app.schemas.user import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register")
def register(payload: UserRegisterRequest, db: DbSession):
    return success(AuthService(db).register(payload))


@router.post("/login")
def login(payload: UserLoginRequest, db: DbSession):
    return success(AuthService(db).login(payload))


@router.get("/me")
def me(current_user: CurrentUser):
    return success(AuthService.to_user_dto(current_user))
