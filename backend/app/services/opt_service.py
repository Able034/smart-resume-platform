import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.resume_optimize_agent import ResumeOptimizationPayload, ResumeOptimizeAgent
from app.core.exceptions import AppException, BAD_REQUEST, NOT_FOUND
from app.models import InternInfo, Job, Opt, ProjectInfo, Resume
from app.schemas.opt import (
    ApplyOptimizationRequest,
    ApplyOptimizationResponse,
    OptDTO,
    OptListItem,
)
from app.services.resume_service import ResumeService


class OptService:
    def __init__(self, db: Session):
        self.db = db

    def optimize(self, resume_id: int, user_id: int, job_id: int | None = None) -> OptDTO:
        self._assert_resume_owner(resume_id, user_id)
        job_content = None
        if job_id is not None:
            job = self.db.get(Job, job_id)
            if not job or job.resume_id != resume_id:
                raise AppException(NOT_FOUND, "Job not found", 404)
            job_content = job.content

        resume = ResumeService(self.db).get_detail_for_user(resume_id, user_id)
        result = ResumeOptimizeAgent().optimize(resume, job_content)
        opt = Opt(
            resume_id=resume_id,
            job_id=job_id,
            content=result.content,
            result_json=(
                result.payload.model_dump_json(by_alias=True) if result.payload else None
            ),
            score=result.score,
            status="NEW",
        )
        self.db.add(opt)
        self.db.commit()
        self.db.refresh(opt)
        return self._to_dto(opt)

    def list_by_resume(self, resume_id: int, user_id: int) -> list[OptListItem]:
        self._assert_resume_owner(resume_id, user_id)
        rows = self.db.scalars(
            select(Opt).where(Opt.resume_id == resume_id).order_by(Opt.created_at.desc())
        ).all()
        return [
            OptListItem(
                opt_id=row.opt_id,
                job_id=row.job_id,
                score=float(row.score) if row.score is not None else None,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get_detail(self, opt_id: int, user_id: int) -> OptDTO:
        opt = self.db.get(Opt, opt_id)
        if not opt:
            raise AppException(NOT_FOUND, "Optimization record not found", 404)
        self._assert_resume_owner(opt.resume_id, user_id)
        return self._to_dto(opt)

    def apply(
        self,
        opt_id: int,
        user_id: int,
        payload: ApplyOptimizationRequest,
    ) -> ApplyOptimizationResponse:
        opt = self.db.get(Opt, opt_id)
        if not opt:
            raise AppException(NOT_FOUND, "Optimization record not found", 404)
        resume = self._get_resume_for_user(opt.resume_id, user_id)
        result = self._load_result_payload(opt)

        applied_skill = False
        applied_project_ids: list[int] = []
        applied_intern_ids: list[int] = []

        if payload.apply_skill and result.skill.optimized:
            resume.skill_name = result.skill.optimized
            applied_skill = True

        if payload.apply_projects:
            allowed_project_ids = set(payload.project_ids or [])
            project_segment_indexes = payload.project_segment_indexes
            for item in result.projects:
                if item.source_id is None or not item.optimized_bullets:
                    continue
                if project_segment_indexes is not None and item.source_id not in project_segment_indexes:
                    continue
                if allowed_project_ids and item.source_id not in allowed_project_ids:
                    continue
                project = self.db.get(ProjectInfo, item.source_id)
                if not project or project.resume_id != opt.resume_id:
                    continue
                if project_segment_indexes is not None and item.segments:
                    project.content = self._join_bullets(
                        self._merge_segments(
                            item.segments,
                            set(project_segment_indexes.get(item.source_id, [])),
                        )
                    )
                else:
                    project.content = self._join_bullets(item.optimized_bullets)
                applied_project_ids.append(project.project_info_id)

        if payload.apply_interns:
            allowed_intern_ids = set(payload.intern_ids or [])
            intern_segment_indexes = payload.intern_segment_indexes
            for item in result.interns:
                if item.source_id is None or not item.optimized_bullets:
                    continue
                if intern_segment_indexes is not None and item.source_id not in intern_segment_indexes:
                    continue
                if allowed_intern_ids and item.source_id not in allowed_intern_ids:
                    continue
                intern = self.db.get(InternInfo, item.source_id)
                if not intern or intern.resume_id != opt.resume_id:
                    continue
                if intern_segment_indexes is not None and item.segments:
                    intern.content = self._join_bullets(
                        self._merge_segments(
                            item.segments,
                            set(intern_segment_indexes.get(item.source_id, [])),
                        )
                    )
                else:
                    intern.content = self._join_bullets(item.optimized_bullets)
                applied_intern_ids.append(intern.intern_info_id)

        if not (applied_skill or applied_project_ids or applied_intern_ids):
            raise AppException(
                BAD_REQUEST,
                "No optimization content was applied. Check resultJson and selected sections.",
                400,
            )

        resume.status = "SAVED"
        opt.status = "USED"
        self.db.commit()
        return ApplyOptimizationResponse(
            opt_id=opt.opt_id,
            resume_id=opt.resume_id,
            applied_skill=applied_skill,
            applied_project_ids=applied_project_ids,
            applied_intern_ids=applied_intern_ids,
            status=opt.status,
        )

    def update_status(self, opt_id: int, user_id: int, status: str) -> None:
        opt = self.db.get(Opt, opt_id)
        if not opt:
            raise AppException(NOT_FOUND, "Optimization record not found", 404)
        self._assert_resume_owner(opt.resume_id, user_id)
        opt.status = status
        self.db.commit()

    def _to_dto(self, opt: Opt) -> OptDTO:
        return OptDTO(
            opt_id=opt.opt_id,
            resume_id=opt.resume_id,
            job_id=opt.job_id,
            content=opt.content,
            result_json=self._safe_json_loads(opt.result_json),
            score=float(opt.score) if opt.score is not None else None,
            status=opt.status,
            created_at=opt.created_at,
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

    def _assert_resume_owner(self, resume_id: int, user_id: int) -> None:
        exists = self.db.scalar(
            select(Resume.resume_id).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
            )
        )
        if not exists:
            raise AppException(NOT_FOUND, "Resume not found", 404)

    def _load_result_payload(self, opt: Opt) -> ResumeOptimizationPayload:
        payload = self._safe_json_loads(opt.result_json)
        if not payload:
            raise AppException(
                BAD_REQUEST,
                "Optimization resultJson is empty. Generate a new optimization first.",
                400,
            )
        return ResumeOptimizationPayload.model_validate(payload)

    def _safe_json_loads(self, value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _join_bullets(self, bullets: list[str]) -> str:
        return "\n".join(
            f"- {bullet.strip().lstrip('-').strip()}"
            for bullet in bullets
            if bullet.strip()
        )

    def _merge_segments(self, segments: list[Any], accepted_indexes: set[int]) -> list[str]:
        return [
            (segment.optimized if segment.segment_index in accepted_indexes else segment.original)
            for segment in segments
            if segment.original or segment.optimized
        ]
