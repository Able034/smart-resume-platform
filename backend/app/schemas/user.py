from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import AppSchema


class UserRegisterRequest(AppSchema):
    account: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr


class UserLoginRequest(AppSchema):
    account: str
    password: str


class UserDTO(AppSchema):
    user_id: int
    account: str
    email: str | None = None
    role: str
    status: str
    register_time: datetime | None = None
    last_login_time: datetime | None = None


class LoginResponse(AppSchema):
    token: str
    user: UserDTO


class AdminUserQuery(AppSchema):
    keyword: str | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 10
