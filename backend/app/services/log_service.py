from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SystemLog
from app.schemas.admin import SystemLogDTO


class LogService:
    def __init__(self, db: Session):
        self.db = db

    def list_logs(
        self,
        keyword: str | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SystemLogDTO], int]:
        query = select(SystemLog)
        count_query = select(func.count()).select_from(SystemLog)
        if keyword:
            condition = (
                SystemLog.action.like(f"%{keyword}%")
                | SystemLog.target_type.like(f"%{keyword}%")
                | SystemLog.target_id.like(f"%{keyword}%")
                | SystemLog.detail.like(f"%{keyword}%")
            )
            query = query.where(condition)
            count_query = count_query.where(condition)
        if action:
            query = query.where(SystemLog.action == action)
            count_query = count_query.where(SystemLog.action == action)

        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(SystemLog.created_at.desc(), SystemLog.log_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [self._to_dto(row) for row in rows], total

    def record(
        self,
        user_id: int | None,
        action: str,
        target_type: str | None = None,
        target_id: str | int | None = None,
        detail: str | None = None,
        ip: str | None = None,
    ) -> SystemLogDTO:
        row = SystemLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=detail,
            ip=ip,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    def _to_dto(self, row: SystemLog) -> SystemLogDTO:
        return SystemLogDTO(
            log_id=row.log_id,
            user_id=row.user_id,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            detail=row.detail,
            ip=row.ip,
            created_at=row.created_at,
        )
