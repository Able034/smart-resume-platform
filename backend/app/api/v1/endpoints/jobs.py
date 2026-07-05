from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.api.request_utils import client_ip
from app.schemas.common import success
from app.schemas.job import JobAnalyzeRequest
from app.services.job_service import JobService
from app.services.log_service import LogService

router = APIRouter()


@router.post("/resumes/{resume_id}/jobs/analyze")
def analyze_job(
    resume_id: int,
    payload: JobAnalyzeRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    result = JobService(db).analyze(
        resume_id,
        current_user.id,
        payload.job_url,
        payload.job_description,
    )
    LogService(db).record(
        user_id=current_user.id,
        action="ANALYZE_JOB",
        target_type="job",
        target_id=result.job_id,
        detail=f"用户 {current_user.account} 为简历 {resume_id} 分析岗位",
        ip=client_ip(request),
    )
    return success(result)


@router.get("/resumes/{resume_id}/jobs")
def list_resume_jobs(resume_id: int, current_user: CurrentUser, db: DbSession):
    return success(JobService(db).list_by_resume(resume_id, current_user.id))


@router.get("/jobs/{job_id}")
def get_job(job_id: int, current_user: CurrentUser, db: DbSession):
    return success(JobService(db).get_detail(job_id, current_user.id))
