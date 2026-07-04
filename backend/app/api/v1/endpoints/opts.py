from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import success
from app.schemas.opt import ApplyOptimizationRequest, OptimizeRequest, OptStatusRequest
from app.services.opt_service import OptService

router = APIRouter()


@router.post("/resumes/{resume_id}/optimize")
def optimize_resume(
    resume_id: int,
    payload: OptimizeRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return success(OptService(db).optimize(resume_id, current_user.id, payload.job_id))


@router.get("/resumes/{resume_id}/opts")
def list_opts(resume_id: int, current_user: CurrentUser, db: DbSession):
    return success(OptService(db).list_by_resume(resume_id, current_user.id))


@router.get("/opts/{opt_id}")
def get_opt(opt_id: int, current_user: CurrentUser, db: DbSession):
    return success(OptService(db).get_detail(opt_id, current_user.id))


@router.post("/opts/{opt_id}/apply")
def apply_opt(
    opt_id: int,
    payload: ApplyOptimizationRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return success(OptService(db).apply(opt_id, current_user.id, payload))


@router.patch("/opts/{opt_id}/status")
def update_opt_status(
    opt_id: int,
    payload: OptStatusRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    OptService(db).update_status(opt_id, current_user.id, payload.status)
    return success(True)
