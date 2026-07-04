from datetime import date, datetime

from pydantic import Field

from app.schemas.common import AppSchema


class EducationInput(AppSchema):
    education_info_id: int | None = None
    university: str
    major: str
    degree: str
    start_time: date
    end_time: date | None = None


class ProjectInput(AppSchema):
    project_info_id: int | None = None
    project_name: str
    role: str | None = None
    introduction: str | None = None
    content: str = ""
    start_time: date | None = None
    end_time: date | None = None


class InternInput(AppSchema):
    intern_info_id: int | None = None
    company: str
    role: str | None = None
    content: str = ""
    start_time: date | None = None
    end_time: date | None = None


class AwardInput(AppSchema):
    award_info_id: int | None = None
    name: str
    award_time: date | None = None


class ResumeUpdateRequest(AppSchema):
    title: str = Field(max_length=100)
    name: str | None = Field(default=None, max_length=100)
    age: int | None = Field(default=None, ge=0, le=120)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    expected_salary: str | None = Field(default=None, max_length=100)
    expected_position: str | None = Field(default=None, max_length=150)
    skill_name: str
    personal_context: str
    status: str = "SAVED"
    educations: list[EducationInput] = Field(default_factory=list)
    projects: list[ProjectInput] = Field(default_factory=list)
    interns: list[InternInput] = Field(default_factory=list)
    awards: list[AwardInput] = Field(default_factory=list)


class StandardResume(AppSchema):
    title: str = "PDF imported resume"
    name: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    email: str | None = None
    phone: str | None = None
    expected_salary: str | None = None
    expected_position: str | None = None
    skill_name: str = ""
    personal_context: str = ""
    status: str = "DRAFT"
    educations: list[EducationInput] = Field(default_factory=list)
    projects: list[ProjectInput] = Field(default_factory=list)
    interns: list[InternInput] = Field(default_factory=list)
    awards: list[AwardInput] = Field(default_factory=list)


class EducationDTO(EducationInput):
    education_info_id: int


class ProjectDTO(ProjectInput):
    project_info_id: int


class InternDTO(InternInput):
    intern_info_id: int


class AwardDTO(AwardInput):
    award_info_id: int


class ResumeDetail(AppSchema):
    resume_id: int
    user_id: int
    resume_template_id: int | None = None
    title: str
    name: str | None = None
    age: int | None = None
    email: str | None = None
    phone: str | None = None
    expected_salary: str | None = None
    expected_position: str | None = None
    skill_name: str
    personal_context: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    educations: list[EducationDTO] = Field(default_factory=list)
    projects: list[ProjectDTO] = Field(default_factory=list)
    interns: list[InternDTO] = Field(default_factory=list)
    awards: list[AwardDTO] = Field(default_factory=list)


class ResumeListItem(AppSchema):
    resume_id: int
    title: str
    status: str
    updated_at: datetime | None = None


class ResumeUploadResponse(AppSchema):
    resume_id: int
    parse_status: str
    resume: ResumeDetail


class GenerateLatexRequest(AppSchema):
    resume_template_id: int


class GenerateLatexResponse(AppSchema):
    resume_id: int
    resume_template_id: int
    latex_file_name: str
    zip_file_name: str
    download_url: str
    warnings: list[str] = Field(default_factory=list)
