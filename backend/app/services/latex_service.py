from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.latex_template_agent import LatexTemplateAgent
from app.core.config import settings
from app.core.exceptions import AppException, NOT_FOUND
from app.models import Resume, ResumeTemplate
from app.schemas.resume import GenerateLatexResponse
from app.services.resume_service import ResumeService


class LatexService:
    def __init__(self, db: Session):
        self.db = db

    def generate(
        self,
        resume_id: int,
        user_id: int,
        resume_template_id: int,
    ) -> GenerateLatexResponse:
        resume = self.db.scalar(
            select(Resume).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
            )
        )
        if not resume:
            raise AppException(NOT_FOUND, "Resume not found", 404)

        template = self.db.scalar(
            select(ResumeTemplate).where(
                ResumeTemplate.resume_template_id == resume_template_id,
                ResumeTemplate.status == "ACTIVE",
            )
        )
        if not template:
            raise AppException(NOT_FOUND, "Template not found", 404)

        detail = ResumeService(self.db).get_detail_for_user(resume_id, user_id)
        template_path = self._resolve_template_path(template.latex)
        output_root = settings.project_root / settings.generated_latex_dir
        package_result = LatexTemplateAgent().generate_package(
            detail,
            template_path=template_path,
            output_root=output_root,
            package_name=f"resume_{resume_id}",
        )

        resume.resume_template_id = resume_template_id
        self.db.commit()

        return GenerateLatexResponse(
            resume_id=resume_id,
            resume_template_id=resume_template_id,
            latex_file_name=package_result.main_file_name,
            zip_file_name=package_result.zip_path.name,
            download_url=f"{settings.api_v1_prefix}/resumes/{resume_id}/latex/download",
            warnings=package_result.warnings,
        )

    def _resolve_template_path(self, latex_path: str) -> Path:
        path = Path(latex_path)
        if not path.is_absolute():
            path = settings.project_root / path
        if not path.exists():
            raise AppException(NOT_FOUND, f"Latex template not found: {latex_path}", 404)
        return path
