from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import AppSchema


class OptimizeRequest(AppSchema):
    job_id: int | None = None


class ApplyOptimizationRequest(AppSchema):
    apply_skill: bool = True
    apply_projects: bool = True
    apply_interns: bool = True
    project_ids: list[int] | None = None
    intern_ids: list[int] | None = None
    project_segment_indexes: dict[int, list[int]] | None = None
    intern_segment_indexes: dict[int, list[int]] | None = None


class ApplyOptimizationResponse(AppSchema):
    opt_id: int
    resume_id: int
    applied_skill: bool = False
    applied_project_ids: list[int] = Field(default_factory=list)
    applied_intern_ids: list[int] = Field(default_factory=list)
    status: str


class OptDTO(AppSchema):
    opt_id: int
    resume_id: int
    job_id: int | None = None
    content: str
    result_json: dict[str, Any] | None = None
    score: float | None = None
    status: str
    created_at: datetime | None = None


class OptListItem(AppSchema):
    opt_id: int
    job_id: int | None = None
    score: float | None = None
    status: str
    created_at: datetime | None = None


class OptStatusRequest(AppSchema):
    status: str
