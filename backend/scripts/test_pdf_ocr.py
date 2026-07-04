import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_PDF_DIR = PROJECT_ROOT / "uploads" / "pdf"

sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pdf_service import PdfService  # noqa: E402


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

    parser = argparse.ArgumentParser(description="Test local PDF OCR extraction.")
    parser.add_argument("pdf", nargs="?", help="PDF path. Defaults to newest uploads/pdf PDF.")
    parser.add_argument(
        "--output",
        help="Optional UTF-8 text output path. Useful when the Windows terminal displays mojibake.",
    )
    args = parser.parse_args()

    pdf_path = get_pdf_path(args.pdf)
    text = PdfService.extract_text_from_path(pdf_path)
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(f"PDF: {pdf_path}")
    print(f"OCR extracted chars: {len(text)}")
    if args.output:
        print(f"UTF-8 output: {output_path}")
    print("\n----- OCR text -----")
    print(text)


if __name__ == "__main__":
    main()
