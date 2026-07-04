from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import success
from app.schemas.job import JobAnalyzeRequest
from app.services.job_service import JobService

router = APIRouter()


@router.post("/resumes/{resume_id}/jobs/analyze")
def analyze_job(
    resume_id: int,
    payload: JobAnalyzeRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return success(
        JobService(db).analyze(
            resume_id,
            current_user.id,
            payload.job_url,
            payload.job_description,
        )
    )


@router.get("/resumes/{resume_id}/jobs")
def list_resume_jobs(resume_id: int, current_user: CurrentUser, db: DbSession):
    return success(JobService(db).list_by_resume(resume_id, current_user.id))


@router.get("/jobs/{job_id}")
def get_job(job_id: int, current_user: CurrentUser, db: DbSession):
    return success(JobService(db).get_detail(job_id, current_user.id))
