import os
import shutil
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import AppException, BAD_REQUEST


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _select_paddle_work_dir() -> Path:
    candidates = [
        os.getenv("PADDLE_OCR_WORK_DIR"),
        r"D:\Temp\SmartResumePaddle",
        str(PROJECT_ROOT / "tmp" / "paddle"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / "write_test.txt"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return path
        except OSError:
            continue
    raise RuntimeError("No writable PaddleOCR work directory is available.")


PADDLE_WORK_DIR = _select_paddle_work_dir()
PADDLE_CACHE_DIR = PADDLE_WORK_DIR / "paddlex_cache"
PADDLE_TMP_DIR = PADDLE_WORK_DIR / "tmp"
PADDLE_HF_DIR = PADDLE_WORK_DIR / "huggingface"
PADDLE_MODELSCOPE_DIR = PADDLE_WORK_DIR / "modelscope"
for directory in (PADDLE_CACHE_DIR, PADDLE_TMP_DIR, PADDLE_HF_DIR, PADDLE_MODELSCOPE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Set these before importing PaddleOCR. Paddle Inference on Windows can fail when
# model files live under a non-ASCII user directory.
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(PADDLE_CACHE_DIR))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
os.environ.setdefault("HF_HOME", str(PADDLE_HF_DIR))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(PADDLE_HF_DIR / "hub"))
os.environ.setdefault("MODELSCOPE_CACHE", str(PADDLE_MODELSCOPE_DIR))
os.environ.setdefault("AISTUDIO_CACHE_HOME", str(PADDLE_WORK_DIR / "aistudio"))
os.environ["TMP"] = str(PADDLE_TMP_DIR)
os.environ["TEMP"] = str(PADDLE_TMP_DIR)
os.environ["TMPDIR"] = str(PADDLE_TMP_DIR)
os.environ.pop("SSLKEYLOGFILE", None)
tempfile.tempdir = str(PADDLE_TMP_DIR)


def _safe_mkdtemp(
    suffix: str | None = None,
    prefix: str | None = None,
    dir: str | os.PathLike[str] | None = None,
) -> str:
    base_dir = Path(dir) if dir else PADDLE_TMP_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    name_prefix = prefix or "tmp"
    name_suffix = suffix or ""
    for _ in range(100):
        path = base_dir / f"{name_prefix}{uuid.uuid4().hex}{name_suffix}"
        try:
            path.mkdir()
            return str(path)
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not create temporary directory under {base_dir}")


class _SafeTemporaryDirectory:
    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
        ignore_cleanup_errors: bool = False,
    ):
        self.name = _safe_mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self.ignore_cleanup_errors = ignore_cleanup_errors

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        shutil.rmtree(self.name, ignore_errors=True)


tempfile.mkdtemp = _safe_mkdtemp
tempfile.TemporaryDirectory = _SafeTemporaryDirectory


@lru_cache(maxsize=1)
def create_ocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError(
            "PaddleOCR is not installed. Install paddleocr and paddlepaddle first."
        ) from exc

    return PaddleOCR(
        lang="ch",
        ocr_version="PP-OCRv4",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


class PdfService:
    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise AppException(BAD_REQUEST, "Only PDF files are supported")

        content = await file.read()
        max_size = settings.max_pdf_size_mb * 1024 * 1024
        if len(content) > max_size:
            raise AppException(BAD_REQUEST, "PDF file is too large")

        return PdfService.extract_text_from_bytes(content)

    @staticmethod
    def extract_text_from_path(pdf_path: str | Path) -> str:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_file}")
        if pdf_file.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF files are supported: {pdf_file}")

        try:
            result = create_ocr().predict(str(pdf_file))
            text = PdfService._collect_ocr_texts(result)
        except RuntimeError as exc:
            raise AppException(BAD_REQUEST, str(exc)) from exc
        except Exception as exc:
            raise AppException(BAD_REQUEST, "PDF OCR extraction failed") from exc

        text = text.strip()
        if not text:
            raise AppException(BAD_REQUEST, "No text was extracted from PDF by OCR")
        return text

    @staticmethod
    def extract_text_from_bytes(content: bytes) -> str:
        temp_dir = settings.project_root / "tmp" / "ocr"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid.uuid4().hex}.pdf"
        try:
            temp_path.write_bytes(content)
            return PdfService.extract_text_from_path(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _collect_ocr_texts(result: Any) -> str:
        texts: list[str] = []
        if result is None:
            return ""
        pages = result if isinstance(result, list) else [result]
        for page in pages:
            PdfService._extend_texts(texts, PdfService._page_to_data(page))
        return "\n".join(text for text in texts if text).strip()

    @staticmethod
    def _page_to_data(page: Any) -> Any:
        json_attr = getattr(page, "json", None)
        if callable(json_attr):
            return json_attr()
        if json_attr is not None:
            return json_attr
        return page

    @staticmethod
    def _extend_texts(texts: list[str], data: Any) -> None:
        if isinstance(data, dict):
            res = data.get("res", data)
            rec_texts = res.get("rec_texts") if isinstance(res, dict) else None
            if isinstance(rec_texts, list):
                texts.extend(str(text).strip() for text in rec_texts if str(text).strip())
                return
            for value in data.values():
                PdfService._extend_texts(texts, value)
            return

        if isinstance(data, tuple) and len(data) >= 2 and isinstance(data[1], tuple):
            text = data[1][0]
            if text:
                texts.append(str(text).strip())
            return

        if isinstance(data, list):
            for item in data:
                PdfService._extend_texts(texts, item)
