import argparse
import json
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_PDF_DIR = PROJECT_ROOT / "uploads" / "pdf"

sys.path.insert(0, str(BACKEND_ROOT))
os.environ.pop("SSLKEYLOGFILE", None)

from app.agents.resume_parse_agent import ResumeParseAgent  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.pdf_service import PdfService  # noqa: E402


def extract_pdf_text(pdf_path: Path) -> str:
    return PdfService.extract_text_from_path(pdf_path)


def get_pdf_path(value: str | None) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        return path

    pdfs = sorted(
        DEFAULT_PDF_DIR.glob("*.pdf"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in: {DEFAULT_PDF_DIR}")
    return pdfs[0]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Test local PDF resume parsing.")
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Optional PDF path. Defaults to the newest file under uploads/pdf.",
    )
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Print extracted PDF text before the parsed JSON.",
    )
    parser.add_argument("--expect-name", help="Fail if parsed name does not match.")
    parser.add_argument(
        "--expect-position",
        help="Fail if parsed expectedPosition does not match.",
    )
    parser.add_argument(
        "--min-projects",
        type=int,
        default=0,
        help="Fail if parsed project count is smaller than this value.",
    )
    parser.add_argument(
        "--min-educations",
        type=int,
        default=0,
        help="Fail if parsed education count is smaller than this value.",
    )
    args = parser.parse_args()

    pdf_path = get_pdf_path(args.pdf)
    pdf_text = extract_pdf_text(pdf_path)

    print(f"PDF: {pdf_path}")
    print(f"LLM_MOCK: {settings.llm_mock}")
    print(f"OCR extracted chars: {len(pdf_text)}")
    if args.show_text:
        print("\n----- Extracted text -----")
        print(pdf_text)

    resume = ResumeParseAgent().parse(pdf_text)
    print("\n----- Parsed resume JSON -----")
    print(
        json.dumps(
            resume.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
    )

    failures: list[str] = []
    if args.expect_name and resume.name != args.expect_name:
        failures.append(f"name expected {args.expect_name!r}, got {resume.name!r}")
    if args.expect_position and resume.expected_position != args.expect_position:
        failures.append(
            "expectedPosition expected "
            f"{args.expect_position!r}, got {resume.expected_position!r}"
        )
    if len(resume.projects) < args.min_projects:
        failures.append(
            f"projects expected at least {args.min_projects}, got {len(resume.projects)}"
        )
    if len(resume.educations) < args.min_educations:
        failures.append(
            "educations expected at least "
            f"{args.min_educations}, got {len(resume.educations)}"
        )
    if failures:
        print("\n----- Assertions failed -----")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
