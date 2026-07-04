import argparse
import json
import logging
import os
import sys
import time
import zipfile
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_PDF = PROJECT_ROOT / "uploads" / "pdf" / "0f5f698a-7aca-4c04-9c03-4579a3fef536.pdf"
DEFAULT_TEMPLATE = PROJECT_ROOT / "Latex" / "1" / "resume" / "resume-zh_CN.tex"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "generated" / "latex"

sys.path.insert(0, str(BACKEND_ROOT))
os.environ.pop("SSLKEYLOGFILE", None)
os.environ["LLM_MOCK"] = "false"

from app.agents.latex_template_agent import LatexTemplateAgent  # noqa: E402
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


logger = logging.getLogger("pdf_to_latex_template1_test")


class PdfToLatexTemplate1Test:
    def __init__(self, pdf_path: Path, template_path: Path, output_root: Path):
        self.pdf_path = pdf_path
        self.template_path = template_path
        self.output_root = output_root

    def run(self) -> dict:
        logger.info("Test started.")
        logger.info("PDF path: %s", self.pdf_path)
        logger.info("Template path: %s", self.template_path)
        logger.info("Output root: %s", self.output_root)
        logger.info("LLM_MOCK: %s", settings.llm_mock)

        start = time.perf_counter()
        pdf_text = self.extract_pdf_text()
        logger.info("PDF text extraction finished. chars=%s elapsed=%.2fs", len(pdf_text), time.perf_counter() - start)

        start = time.perf_counter()
        logger.info("ResumeParseAgent started. fallback=false")
        parsed_resume = ResumeParseAgent(allow_fallback=False).parse(pdf_text)
        logger.info(
            "ResumeParseAgent finished. name=%s education=%s projects=%s interns=%s awards=%s elapsed=%.2fs",
            parsed_resume.name,
            len(parsed_resume.educations),
            len(parsed_resume.projects),
            len(parsed_resume.interns),
            len(parsed_resume.awards),
            time.perf_counter() - start,
        )

        start = time.perf_counter()
        logger.info("Converting StandardResume to ResumeDetail.")
        resume_detail = self.to_resume_detail(parsed_resume)
        logger.info("ResumeDetail conversion finished. elapsed=%.2fs", time.perf_counter() - start)

        start = time.perf_counter()
        logger.info("LatexTemplateAgent started. fallback=false")
        package = LatexTemplateAgent(allow_fallback=False).generate_package(
            resume_detail,
            template_path=self.template_path,
            output_root=self.output_root,
            package_name=f"test_template1_{self.pdf_path.stem[:8]}",
        )
        logger.info(
            "LatexTemplateAgent finished. packageDir=%s zip=%s elapsed=%.2fs",
            package.package_dir,
            package.zip_path,
            time.perf_counter() - start,
        )

        start = time.perf_counter()
        logger.info("Inspecting generated zip.")
        zip_entries = self.inspect_zip(package.zip_path)
        logger.info("Zip inspection finished. entries=%s elapsed=%.2fs", len(zip_entries), time.perf_counter() - start)
        required_entries = [
            "resume-zh_CN.tex",
            "resume.cls",
            "fontawesome.sty",
            "fonts/zh_CN-Adobe/AdobeSongStd-Light.otf",
        ]
        missing_entries = [entry for entry in required_entries if entry not in zip_entries]

        return {
            "pdf": str(self.pdf_path),
            "template": str(self.template_path),
            "llmMock": settings.llm_mock,
            "requireAgent": True,
            "allowFallback": False,
            "parsed": {
                "title": parsed_resume.title,
                "name": parsed_resume.name,
                "email": parsed_resume.email,
                "phone": parsed_resume.phone,
                "expectedPosition": parsed_resume.expected_position,
                "educationCount": len(parsed_resume.educations),
                "projectCount": len(parsed_resume.projects),
                "internCount": len(parsed_resume.interns),
                "awardCount": len(parsed_resume.awards),
            },
            "latex": {
                "mainFileName": package.main_file_name,
                "packageDir": str(package.package_dir),
                "zipPath": str(package.zip_path),
                "zipEntryCount": len(zip_entries),
                "missingRequiredEntries": missing_entries,
                "warnings": package.warnings,
            },
        }

    def extract_pdf_text(self) -> str:
        logger.info("Extracting PDF text by OCR.")
        return PdfService.extract_text_from_path(self.pdf_path)

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

    def inspect_zip(self, zip_path: Path) -> set[str]:
        if not zip_path.exists():
            raise FileNotFoundError(f"Latex zip file was not generated: {zip_path}")
        with zipfile.ZipFile(zip_path) as archive:
            return {entry.filename.replace("\\", "/") for entry in archive.infolist()}


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
        description="End-to-end test: PDF parse agent -> LaTeX template 1 zip package."
    )
    parser.add_argument("pdf", nargs="?", help="PDF path. Defaults to the requested sample PDF.")
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE),
        help="Template 1 main .tex path.",
    )
    args = parser.parse_args()

    try:
        result = PdfToLatexTemplate1Test(
            pdf_path=resolve_path(args.pdf, DEFAULT_PDF),
            template_path=resolve_path(args.template, DEFAULT_TEMPLATE),
            output_root=DEFAULT_OUTPUT_ROOT,
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
