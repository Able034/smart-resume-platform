from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.common import AppSchema


class JobAnalyzeRequest(AppSchema):
    job_url: str | None = Field(default=None, max_length=4096)
    job_description: str | None = Field(default=None, max_length=50000)

    @model_validator(mode="after")
    def require_url_or_description(self) -> "JobAnalyzeRequest":
        self.job_url = self.job_url.strip() if self.job_url else None
        self.job_description = (
            self.job_description.strip() if self.job_description else None
        )
        if not self.job_url and not self.job_description:
            raise ValueError("Job URL or job description is required.")
        return self


class JobSummary(AppSchema):
    job_type: str = ""
    domain: str = ""
    function: str = ""
    seniority: str = ""
    work_mode: str = ""
    tldr: str = ""


class RequirementMapping(AppSchema):
    requirement: str = ""
    importance: str = ""
    resume_evidence: list[str] = Field(default_factory=list)
    gap: str = ""
    remedy: str = ""


class ResumeMatchAnalysis(AppSchema):
    key_matches: list[str] = Field(default_factory=list)
    mappings: list[RequirementMapping] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    remedies: list[str] = Field(default_factory=list)


class LevelStrategy(AppSchema):
    inferred_level: str = ""
    level_signals: list[str] = Field(default_factory=list)
    positioning: str = ""
    honest_seniority_pitch: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class CompensationMarket(AppSchema):
    salary_range: str = ""
    compensation_reputation: str = ""
    market_demand: str = ""
    evidence: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class CustomizationPlan(AppSchema):
    resume_changes: list[str] = Field(default_factory=list)
    linkedin_changes: list[str] = Field(default_factory=list)
    keyword_focus: list[str] = Field(default_factory=list)
    rewrite_focus: list[str] = Field(default_factory=list)


class InterviewStoryPrompt(AppSchema):
    requirement: str = ""
    story_angle: str = ""
    resume_evidence: str = ""
    star_r_outline: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)


class InterviewPlan(AppSchema):
    star_story_prompts: list[InterviewStoryPrompt] = Field(default_factory=list)
    likely_questions: list[str] = Field(default_factory=list)
    prep_tasks: list[str] = Field(default_factory=list)


class JobAuthenticityCheck(AppSchema):
    verdict: str = ""
    confidence: str = ""
    active_signals: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    stop_reason: str = ""


class ScoreDimension(AppSchema):
    name: str = ""
    score: float | None = Field(default=None, ge=0, le=100)
    weight: float | None = Field(default=None, ge=0, le=1)
    rationale: str = ""


class JobScoring(AppSchema):
    dimensions: list[ScoreDimension] = Field(default_factory=list)
    global_score: float | None = Field(default=None, ge=0, le=100)
    recommendation: str = ""
    score_band: str = ""


class JobAnalysisResult(AppSchema):
    match_score: float | None = None
    suitable: bool | None = None
    confidence_source: list[str] = Field(default_factory=list)
    analysis: str = ""
    job_archetype: str = ""
    job_summary: JobSummary = Field(default_factory=JobSummary)
    resume_match: ResumeMatchAnalysis = Field(default_factory=ResumeMatchAnalysis)
    level_strategy: LevelStrategy = Field(default_factory=LevelStrategy)
    compensation_market: CompensationMarket = Field(default_factory=CompensationMarket)
    customization_plan: CustomizationPlan = Field(default_factory=CustomizationPlan)
    interview_plan: InterviewPlan = Field(default_factory=InterviewPlan)
    authenticity_check: JobAuthenticityCheck = Field(default_factory=JobAuthenticityCheck)
    scoring: JobScoring = Field(default_factory=JobScoring)
    optimization_focus: list[str] = Field(default_factory=list)
    star_story_focus: list[str] = Field(default_factory=list)
    resume_rewrite_focus: list[str] = Field(default_factory=list)


class JobDTO(AppSchema):
    job_id: int
    resume_id: int
    job_url: str
    job_name: str | None = None
    company: str | None = None
    content: str
    status: str
    created_at: datetime | None = None


class JobAnalyzeResponse(JobDTO, JobAnalysisResult):
    pass


class JobListItem(AppSchema):
    job_id: int
    job_name: str | None = None
    company: str | None = None
    status: str
    created_at: datetime | None = None
