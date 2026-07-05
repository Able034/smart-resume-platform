import re
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException, BAD_REQUEST
from app.models import ResumeTemplate
from app.schemas.template import ResumeTemplateDTO


class TemplateService:
    main_file_candidates = (
        "resume-zh_CN.tex",
        "resume.tex",
        "main.tex",
        "cv.tex",
        "resume_photo.tex",
    )

    def __init__(self, db: Session):
        self.db = db

    def list_active(self) -> list[ResumeTemplateDTO]:
        rows = self.db.scalars(
            select(ResumeTemplate)
            .where(ResumeTemplate.status == "ACTIVE")
            .order_by(ResumeTemplate.resume_template_id.asc())
        ).all()
        return [
            ResumeTemplateDTO(
                resume_template_id=row.resume_template_id,
                template_name=row.template_name,
                latex=row.latex,
                preview_url=row.preview_url,
                status=row.status,
            )
            for row in rows
        ]

    def create_from_upload(
        self,
        template_name: str,
        filename: str,
        content: bytes,
    ) -> ResumeTemplateDTO:
        template_name = template_name.strip()
        if not template_name:
            raise AppException(BAD_REQUEST, "Template name is required.", 400)
        if not filename:
            raise AppException(BAD_REQUEST, "Template file is required.", 400)
        if not content:
            raise AppException(BAD_REQUEST, "Template file is empty.", 400)
        if len(content) > 20 * 1024 * 1024:
            raise AppException(BAD_REQUEST, "Template file is too large.", 400)

        suffix = Path(filename).suffix.lower()
        if suffix not in {".tex", ".zip"}:
            raise AppException(BAD_REQUEST, "Only .tex and .zip template files are supported.", 400)

        upload_dir = settings.project_root / "templates" / "resume" / "uploaded" / uuid.uuid4().hex
        upload_dir.mkdir(parents=True, exist_ok=False)

        if suffix == ".tex":
            safe_name = self._safe_filename(filename, default="resume.tex")
            main_path = upload_dir / safe_name
            main_path.write_bytes(content)
        else:
            self._extract_zip(content, upload_dir)
            main_path = self._find_main_template_file(upload_dir)

        row = ResumeTemplate(
            template_name=template_name,
            latex=self._relative_path(main_path),
            preview_url=None,
            status="ACTIVE",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    def _to_dto(self, row: ResumeTemplate) -> ResumeTemplateDTO:
        return ResumeTemplateDTO(
            resume_template_id=row.resume_template_id,
            template_name=row.template_name,
            latex=row.latex,
            preview_url=row.preview_url,
            status=row.status,
        )

    def _extract_zip(self, content: bytes, output_dir: Path) -> None:
        zip_path = output_dir / "source.zip"
        zip_path.write_bytes(content)
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    target = output_dir / item.filename
                    try:
                        target.resolve().relative_to(output_dir.resolve())
                    except ValueError as exc:
                        raise AppException(BAD_REQUEST, "Template zip contains unsafe paths.", 400) from exc
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source:
                        target.write_bytes(source.read())
        except zipfile.BadZipFile as exc:
            raise AppException(BAD_REQUEST, "Template zip file is invalid.", 400) from exc
        finally:
            zip_path.unlink(missing_ok=True)

    def _find_main_template_file(self, template_dir: Path) -> Path:
        for candidate in self.main_file_candidates:
            matches = sorted(template_dir.rglob(candidate))
            if matches:
                return matches[0]
        tex_files = sorted(template_dir.rglob("*.tex"))
        if tex_files:
            return tex_files[0]
        raise AppException(BAD_REQUEST, "Template zip does not contain a .tex file.", 400)

    def _safe_filename(self, filename: str, default: str) -> str:
        name = Path(filename).name
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
        return name if name.lower().endswith(".tex") else default

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(settings.project_root.resolve()).as_posix()
