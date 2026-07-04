from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import success
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("")
def list_templates(current_user: CurrentUser, db: DbSession):
    return success(TemplateService(db).list_active())
