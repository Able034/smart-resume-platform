from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.api.request_utils import client_ip
from app.core.config import settings
from app.core.exceptions import AppException, NOT_FOUND
from app.schemas.common import PageData, success
from app.schemas.resume import GenerateLatexRequest, ResumeUpdateRequest
from app.services.latex_service import LatexService
from app.services.log_service import LogService
from app.services.pdf_service import PdfService
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    pdf_text = await PdfService.extract_text(file)
    result = ResumeService(db).create_from_pdf_text(current_user.id, pdf_text)
    LogService(db).record(
        user_id=current_user.id,
        action="UPLOAD_RESUME",
        target_type="resume",
        target_id=result.resume_id,
        detail=f"用户 {current_user.account} 上传并解析 PDF 简历 {file.filename or ''}".strip(),
        ip=client_ip(request),
    )
    return success(result)


@router.get("")
def list_resumes(
    current_user: CurrentUser,
    db: DbSession,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    pageSize: int = 10,
):
    items, total = ResumeService(db).list_by_user(
        current_user.id, keyword=keyword, status=status, page=page, page_size=pageSize
    )
    return success(PageData(items=items, page=page, page_size=pageSize, total=total))


@router.get("/{resume_id}")
def get_resume(resume_id: int, current_user: CurrentUser, db: DbSession):
    return success(ResumeService(db).get_detail_for_user(resume_id, current_user.id))


@router.put("/{resume_id}")
def update_resume(
    resume_id: int,
    payload: ResumeUpdateRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    result = ResumeService(db).update_resume(resume_id, current_user.id, payload)
    LogService(db).record(
        user_id=current_user.id,
        action="UPDATE_RESUME",
        target_type="resume",
        target_id=resume_id,
        detail=f"用户 {current_user.account} 保存简历 {payload.title}",
        ip=client_ip(request),
    )
    return success(result)


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    ResumeService(db).soft_delete(resume_id, current_user.id)
    LogService(db).record(
        user_id=current_user.id,
        action="DELETE_RESUME",
        target_type="resume",
        target_id=resume_id,
        detail=f"用户 {current_user.account} 删除简历 {resume_id}",
        ip=client_ip(request),
    )
    return success(True)


@router.post("/{resume_id}/generate-latex")
def generate_latex(
    resume_id: int,
    payload: GenerateLatexRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    result = LatexService(db).generate(resume_id, current_user.id, payload.resume_template_id)
    LogService(db).record(
        user_id=current_user.id,
        action="GENERATE_LATEX",
        target_type="resume",
        target_id=resume_id,
        detail=(
            f"用户 {current_user.account} 使用模板 "
            f"{payload.resume_template_id} 生成 LaTeX 简历包"
        ),
        ip=client_ip(request),
    )
    return success(result)


@router.get("/{resume_id}/latex/download")
def download_latex(
    resume_id: int,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
):
    ResumeService(db).get_detail_for_user(resume_id, current_user.id)
    file_path = settings.project_root / settings.generated_latex_dir / f"resume_{resume_id}.zip"
    if not file_path.exists():
        raise AppException(NOT_FOUND, "Latex zip file not found", 404)
    LogService(db).record(
        user_id=current_user.id,
        action="DOWNLOAD_LATEX",
        target_type="resume",
        target_id=resume_id,
        detail=f"用户 {current_user.account} 下载 LaTeX 简历包",
        ip=client_ip(request),
    )
    return FileResponse(
        file_path,
        media_type="application/zip",
        filename=f"resume_{resume_id}.zip",
    )
