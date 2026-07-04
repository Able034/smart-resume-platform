from app.schemas.common import AppSchema


class ResumeTemplateDTO(AppSchema):
    resume_template_id: int
    template_name: str
    latex: str
    preview_url: str | None = None
    status: str
