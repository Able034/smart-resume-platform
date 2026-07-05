from datetime import datetime

from app.schemas.common import AppSchema


class SystemLogDTO(AppSchema):
    log_id: int
    user_id: int | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    detail: str | None = None
    ip: str | None = None
    created_at: datetime | None = None
