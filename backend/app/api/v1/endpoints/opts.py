from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.api.request_utils import client_ip
from app.schemas.common import success
from app.schemas.opt import ApplyOptimizationRequest, OptimizeRequest, OptStatusRequest
from app.services.log_service import LogService
from app.services.opt_service import OptService

router = APIRouter()


@router.post("/resumes/{resume_id}/optimize")
def optimize_resume(
    resume_id: int,
    payload: OptimizeRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    result = OptService(db).optimize(resume_id, current_user.id, payload.job_id)
    LogService(db).record(
        user_id=current_user.id,
        action="OPTIMIZE_RESUME",
        target_type="opt",
        target_id=result.opt_id,
        detail=f"用户 {current_user.account} 为简历 {resume_id} 生成优化建议",
        ip=client_ip(request),
    )
    return success(result)


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
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    result = OptService(db).apply(opt_id, current_user.id, payload)
    LogService(db).record(
        user_id=current_user.id,
        action="APPLY_OPTIMIZATION",
        target_type="opt",
        target_id=opt_id,
        detail=f"用户 {current_user.account} 采纳优化建议 {opt_id}",
        ip=client_ip(request),
    )
    return success(result)


@router.patch("/opts/{opt_id}/status")
def update_opt_status(
    opt_id: int,
    payload: OptStatusRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    OptService(db).update_status(opt_id, current_user.id, payload.status)
    LogService(db).record(
        user_id=current_user.id,
        action="UPDATE_OPT_STATUS",
        target_type="opt",
        target_id=opt_id,
        detail=f"用户 {current_user.account} 将优化建议 {opt_id} 状态改为 {payload.status}",
        ip=client_ip(request),
    )
    return success(True)
