from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.exceptions import AppException, NOT_FOUND
from app.schemas.common import PageData, success
from app.schemas.resume import GenerateLatexRequest, ResumeUpdateRequest
from app.services.latex_service import LatexService
from app.services.pdf_service import PdfService
from app.services.resume_service import ResumeService

router = APIRouter()


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile, current_user: CurrentUser, db: DbSession):
    pdf_text = await PdfService.extract_text(file)
    result = ResumeService(db).create_from_pdf_text(current_user.id, pdf_text)
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
    current_user: CurrentUser,
    db: DbSession,
):
    return success(ResumeService(db).update_resume(resume_id, current_user.id, payload))


@router.delete("/{resume_id}")
def delete_resume(resume_id: int, current_user: CurrentUser, db: DbSession):
    ResumeService(db).soft_delete(resume_id, current_user.id)
    return success(True)


@router.post("/{resume_id}/generate-latex")
def generate_latex(
    resume_id: int,
    payload: GenerateLatexRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return success(
        LatexService(db).generate(resume_id, current_user.id, payload.resume_template_id)
    )


@router.get("/{resume_id}/latex/download")
def download_latex(resume_id: int, current_user: CurrentUser, db: DbSession):
    ResumeService(db).get_detail_for_user(resume_id, current_user.id)
    file_path = settings.project_root / settings.generated_latex_dir / f"resume_{resume_id}.zip"
    if not file_path.exists():
        raise AppException(NOT_FOUND, "Latex zip file not found", 404)
    return FileResponse(
        file_path,
        media_type="application/zip",
        filename=f"resume_{resume_id}.zip",
    )
