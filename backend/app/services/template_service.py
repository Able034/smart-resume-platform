from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResumeTemplate
from app.schemas.template import ResumeTemplateDTO


class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def list_active(self) -> list[ResumeTemplateDTO]:
        rows = self.db.scalars(
            select(ResumeTemplate)
            .where(ResumeTemplate.status == "ACTIVE")
            .order_by(ResumeTemplate.resume_template_id.asc())
        ).all()
        return [
            ResumeTemplateDTO(
                resume_template_id=row.resume_template_id,
                template_name=row.template_name,
                latex=row.latex,
                preview_url=row.preview_url,
                status=row.status,
            )
            for row in rows
        ]
