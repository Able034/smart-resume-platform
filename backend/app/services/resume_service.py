from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.agents.resume_parse_agent import ResumeParseAgent
from app.core.exceptions import AppException, NOT_FOUND
from app.models import AwardInfo, EducationInfo, InternInfo, ProjectInfo, Resume
from app.schemas.resume import (
    AwardDTO,
    EducationDTO,
    InternDTO,
    ProjectDTO,
    ResumeDetail,
    ResumeListItem,
    ResumeUpdateRequest,
    ResumeUploadResponse,
    StandardResume,
)


class ResumeService:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(
        self,
        user_id: int,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ResumeListItem], int]:
        query = select(Resume).where(Resume.user_id == user_id, Resume.deleted_at.is_(None))
        count_query = select(func.count()).select_from(Resume).where(
            Resume.user_id == user_id, Resume.deleted_at.is_(None)
        )
        if keyword:
            query = query.where(Resume.title.like(f"%{keyword}%"))
            count_query = count_query.where(Resume.title.like(f"%{keyword}%"))
        if status:
            query = query.where(Resume.status == status)
            count_query = count_query.where(Resume.status == status)

        total = self.db.scalar(count_query) or 0
        rows = self.db.scalars(
            query.order_by(Resume.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [
            ResumeListItem(
                resume_id=row.resume_id,
                title=row.title,
                status=row.status,
                updated_at=row.updated_at,
            )
            for row in rows
        ], total

    def create_from_pdf_text(self, user_id: int, pdf_text: str) -> ResumeUploadResponse:
        standard_resume = ResumeParseAgent().parse(pdf_text)
        resume = self._create_resume(user_id, standard_resume)
        detail = self.get_detail_for_user(resume.resume_id, user_id)
        return ResumeUploadResponse(
            resume_id=resume.resume_id,
            parse_status="PARSED",
            resume=detail,
        )

    def get_detail_for_user(self, resume_id: int, user_id: int) -> ResumeDetail:
        resume = self._get_resume_for_user(resume_id, user_id)
        educations = self.db.scalars(
            select(EducationInfo).where(EducationInfo.resume_id == resume_id)
        ).all()
        projects = self.db.scalars(
            select(ProjectInfo).where(ProjectInfo.resume_id == resume_id)
        ).all()
        interns = self.db.scalars(
            select(InternInfo).where(InternInfo.resume_id == resume_id)
        ).all()
        awards = self.db.scalars(
            select(AwardInfo).where(AwardInfo.resume_id == resume_id)
        ).all()
        return ResumeDetail(
            resume_id=resume.resume_id,
            user_id=resume.user_id,
            resume_template_id=resume.resume_template_id,
            title=resume.title,
            name=resume.name,
            age=resume.age,
            email=resume.email,
            phone=resume.phone,
            expected_salary=resume.expected_salary,
            expected_position=resume.expected_position,
            skill_name=resume.skill_name,
            personal_context=resume.personal_context,
            status=resume.status,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
            educations=[
                EducationDTO(
                    education_info_id=item.education_info_id,
                    university=item.university,
                    major=item.major,
                    degree=item.degree,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for item in educations
            ],
            projects=[
                ProjectDTO(
                    project_info_id=item.project_info_id,
                    project_name=item.project_name,
                    role=item.role,
                    introduction=item.introduction,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for item in projects
            ],
            interns=[
                InternDTO(
                    intern_info_id=item.intern_info_id,
                    company=item.company,
                    role=item.role,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for item in interns
            ],
            awards=[
                AwardDTO(
                    award_info_id=item.award_info_id,
                    name=item.name,
                    award_time=item.award_time,
                )
                for item in awards
            ],
        )

    def update_resume(
        self,
        resume_id: int,
        user_id: int,
        payload: ResumeUpdateRequest,
    ) -> dict[str, int | str]:
        resume = self._get_resume_for_user(resume_id, user_id)
        resume.title = payload.title
        resume.name = payload.name
        resume.age = payload.age
        resume.email = payload.email
        resume.phone = payload.phone
        resume.expected_salary = payload.expected_salary
        resume.expected_position = payload.expected_position
        resume.skill_name = payload.skill_name
        resume.personal_context = payload.personal_context
        resume.status = payload.status

        self._replace_detail_rows(resume_id, payload)
        self.db.commit()
        return {"resume_id": resume_id, "status": resume.status}

    def soft_delete(self, resume_id: int, user_id: int) -> None:
        resume = self._get_resume_for_user(resume_id, user_id)
        resume.deleted_at = datetime.now()
        resume.status = "ARCHIVED"
        self.db.commit()

    def _create_resume(self, user_id: int, standard_resume: StandardResume) -> Resume:
        resume = Resume(
            user_id=user_id,
            title=standard_resume.title,
            name=standard_resume.name,
            age=standard_resume.age,
            email=standard_resume.email,
            phone=standard_resume.phone,
            expected_salary=standard_resume.expected_salary,
            expected_position=standard_resume.expected_position,
            skill_name=standard_resume.skill_name,
            personal_context=standard_resume.personal_context,
            status=standard_resume.status or "DRAFT",
        )
        self.db.add(resume)
        self.db.flush()
        self._replace_detail_rows(resume.resume_id, standard_resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def _replace_detail_rows(
        self,
        resume_id: int,
        payload: ResumeUpdateRequest | StandardResume,
    ) -> None:
        self.db.execute(delete(EducationInfo).where(EducationInfo.resume_id == resume_id))
        self.db.execute(delete(ProjectInfo).where(ProjectInfo.resume_id == resume_id))
        self.db.execute(delete(InternInfo).where(InternInfo.resume_id == resume_id))
        self.db.execute(delete(AwardInfo).where(AwardInfo.resume_id == resume_id))

        for item in payload.educations:
            self.db.add(
                EducationInfo(
                    resume_id=resume_id,
                    university=item.university,
                    major=item.major,
                    degree=item.degree,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
            )
        for item in payload.projects:
            self.db.add(
                ProjectInfo(
                    resume_id=resume_id,
                    project_name=item.project_name,
                    role=item.role,
                    introduction=item.introduction,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
            )
        for item in payload.interns:
            self.db.add(
                InternInfo(
                    resume_id=resume_id,
                    company=item.company,
                    role=item.role,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
            )
        for item in payload.awards:
            self.db.add(
                AwardInfo(
                    resume_id=resume_id,
                    name=item.name,
                    award_time=item.award_time,
                )
            )

    def _get_resume_for_user(self, resume_id: int, user_id: int) -> Resume:
        resume = self.db.scalar(
            select(Resume).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
            )
        )
        if not resume:
            raise AppException(NOT_FOUND, "Resume not found", 404)
        return resume
