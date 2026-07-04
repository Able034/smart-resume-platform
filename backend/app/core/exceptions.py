from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


BAD_REQUEST = 40001
UNAUTHORIZED = 40101
FORBIDDEN = 40301
NOT_FOUND = 40401
CONFLICT = 40901
SERVER_ERROR = 50001
