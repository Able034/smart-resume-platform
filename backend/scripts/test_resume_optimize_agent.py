import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_PDF = PROJECT_ROOT / "uploads" / "pdf" / "0f5f698a-7aca-4c04-9c03-4579a3fef536.pdf"

sys.path.insert(0, str(BACKEND_ROOT))
os.environ.pop("SSLKEYLOGFILE", None)
os.environ["LLM_MOCK"] = "false"

from app.agents.resume_optimize_agent import ResumeOptimizeAgent  # noqa: E402
from app.agents.resume_parse_agent import ResumeParseAgent  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.pdf_service import PdfService  # noqa: E402
from app.schemas.resume import (  # noqa: E402
    AwardDTO,
    EducationDTO,
    InternDTO,
    ProjectDTO,
    ResumeDetail,
    StandardResume,
)


logger = logging.getLogger("resume_optimize_agent_test")


class ResumeOptimizeAgentTest:
    def __init__(self, pdf_path: Path, job_file: Path | None = None):
        self.pdf_path = pdf_path
        self.job_file = job_file

    def run(self) -> dict:
        logger.info("Test started.")
        logger.info("PDF path: %s", self.pdf_path)
        logger.info("Job file: %s", self.job_file)
        logger.info("LLM_MOCK: %s", settings.llm_mock)

        start = time.perf_counter()
        pdf_text = self.extract_pdf_text()
        logger.info(
            "PDF text extraction finished. chars=%s elapsed=%.2fs",
            len(pdf_text),
            time.perf_counter() - start,
        )

        start = time.perf_counter()
        logger.info("ResumeParseAgent started. fallback=false")
        parsed_resume = ResumeParseAgent(allow_fallback=False).parse(pdf_text)
        logger.info(
            "ResumeParseAgent finished. name=%s projects=%s interns=%s elapsed=%.2fs",
            parsed_resume.name,
            len(parsed_resume.projects),
            len(parsed_resume.interns),
            time.perf_counter() - start,
        )

        resume_detail = self.to_resume_detail(parsed_resume)
        job_content = self.read_job_content()

        start = time.perf_counter()
        logger.info("ResumeOptimizeAgent started. fallback=false")
        result = ResumeOptimizeAgent(allow_fallback=False).optimize(
            resume_detail,
            job_content=job_content,
        )
        logger.info(
            "ResumeOptimizeAgent finished. score=%s elapsed=%.2fs",
            result.score,
            time.perf_counter() - start,
        )

        return {
            "pdf": str(self.pdf_path),
            "jobFile": str(self.job_file) if self.job_file else None,
            "llmMock": settings.llm_mock,
            "requireAgent": True,
            "allowFallback": False,
            "parsed": {
                "title": parsed_resume.title,
                "name": parsed_resume.name,
                "email": parsed_resume.email,
                "phone": parsed_resume.phone,
                "expectedPosition": parsed_resume.expected_position,
                "projectCount": len(parsed_resume.projects),
                "internCount": len(parsed_resume.interns),
            },
            "optimization": {
                "score": result.score,
                "content": result.content,
                "payload": (
                    result.payload.model_dump(mode="json", by_alias=True)
                    if result.payload
                    else None
                ),
            },
        }

    def extract_pdf_text(self) -> str:
        return PdfService.extract_text_from_path(self.pdf_path)

    def read_job_content(self) -> str | None:
        if not self.job_file:
            return None
        if not self.job_file.exists():
            raise FileNotFoundError(f"Job file not found: {self.job_file}")
        return self.job_file.read_text(encoding="utf-8")

    def to_resume_detail(self, resume: StandardResume) -> ResumeDetail:
        return ResumeDetail(
            resume_id=0,
            user_id=0,
            resume_template_id=1,
            title=resume.title,
            name=resume.name,
            age=resume.age,
            email=resume.email,
            phone=resume.phone,
            expected_salary=resume.expected_salary,
            expected_position=resume.expected_position,
            skill_name=resume.skill_name,
            personal_context=resume.personal_context,
            status=resume.status,
            educations=[
                EducationDTO(
                    education_info_id=index,
                    university=item.university,
                    major=item.major,
                    degree=item.degree,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for index, item in enumerate(resume.educations, start=1)
            ],
            projects=[
                ProjectDTO(
                    project_info_id=index,
                    project_name=item.project_name,
                    role=item.role,
                    introduction=item.introduction,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for index, item in enumerate(resume.projects, start=1)
            ],
            interns=[
                InternDTO(
                    intern_info_id=index,
                    company=item.company,
                    role=item.role,
                    content=item.content,
                    start_time=item.start_time,
                    end_time=item.end_time,
                )
                for index, item in enumerate(resume.interns, start=1)
            ],
            awards=[
                AwardDTO(
                    award_info_id=index,
                    name=item.name,
                    award_time=item.award_time,
                )
                for index, item in enumerate(resume.awards, start=1)
            ],
        )


def resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )

    parser = argparse.ArgumentParser(
        description="End-to-end test: PDF parse agent -> resume optimization agent."
    )
    parser.add_argument("pdf", nargs="?", help="PDF path. Defaults to the sample PDF.")
    parser.add_argument("--job-file", help="Optional local text file containing job content.")
    args = parser.parse_args()

    try:
        result = ResumeOptimizeAgentTest(
            pdf_path=resolve_path(args.pdf, DEFAULT_PDF),
            job_file=resolve_path(args.job_file, Path()) if args.job_file else None,
        ).run()
    except Exception as exc:
        logger.exception("Test failed.")
        print(
            json.dumps(
                {
                    "ok": False,
                    "requireAgent": True,
                    "allowFallback": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise

    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
