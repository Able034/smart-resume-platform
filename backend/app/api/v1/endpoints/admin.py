from fastapi import APIRouter, File, Form, Request, UploadFile

from app.api.deps import CurrentAdmin, DbSession
from app.api.request_utils import client_ip
from app.schemas.common import PageData, success
from app.services.admin_service import AdminService
from app.services.log_service import LogService
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("/users")
def list_users(
    current_admin: CurrentAdmin,
    db: DbSession,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    pageSize: int = 10,
):
    items, total = AdminService(db).list_users(
        keyword=keyword, status=status, page=page, page_size=pageSize
    )
    return success(PageData(items=items, page=page, page_size=pageSize, total=total))


@router.patch("/users/{user_id}/disable")
def disable_user(user_id: int, request: Request, current_admin: CurrentAdmin, db: DbSession):
    result = AdminService(db).set_user_status(user_id, "DISABLED")
    LogService(db).record(
        user_id=current_admin.id,
        action="DISABLE_USER",
        target_type="user_account",
        target_id=user_id,
        detail=f"管理员 {current_admin.account} 禁用用户 {result.account}",
        ip=client_ip(request),
    )
    return success(result)


@router.patch("/users/{user_id}/enable")
def enable_user(user_id: int, request: Request, current_admin: CurrentAdmin, db: DbSession):
    result = AdminService(db).set_user_status(user_id, "ACTIVE")
    LogService(db).record(
        user_id=current_admin.id,
        action="ENABLE_USER",
        target_type="user_account",
        target_id=user_id,
        detail=f"管理员 {current_admin.account} 启用用户 {result.account}",
        ip=client_ip(request),
    )
    return success(result)


@router.get("/logs")
def list_logs(
    current_admin: CurrentAdmin,
    db: DbSession,
    keyword: str | None = None,
    action: str | None = None,
    page: int = 1,
    pageSize: int = 20,
):
    items, total = LogService(db).list_logs(
        keyword=keyword,
        action=action,
        page=page,
        page_size=pageSize,
    )
    return success(PageData(items=items, page=page, page_size=pageSize, total=total))


@router.post("/resume-templates/upload")
async def upload_resume_template(
    request: Request,
    current_admin: CurrentAdmin,
    db: DbSession,
    templateName: str = Form(...),
    file: UploadFile = File(...),
):
    content = await file.read()
    result = TemplateService(db).create_from_upload(
        template_name=templateName,
        filename=file.filename or "",
        content=content,
    )
    LogService(db).record(
        user_id=current_admin.id,
        action="UPLOAD_TEMPLATE",
        target_type="resume_template",
        target_id=result.resume_template_id,
        detail=f"管理员 {current_admin.account} 上传模板 {result.template_name}",
        ip=client_ip(request),
    )
    return success(result)
