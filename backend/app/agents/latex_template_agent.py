from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
import shutil
import zipfile

from langchain_core.prompts import ChatPromptTemplate

from app.agents.base import BaseAgent
from app.schemas.resume import ResumeDetail


@dataclass
class LatexGenerateResult:
    latex_code: str
    warnings: list[str]


@dataclass
class LatexTemplateReadResult:
    template_root: Path
    main_template_path: Path
    main_template_source: str


@dataclass
class LatexPackageResult:
    latex_code: str
    main_file_name: str
    package_dir: Path
    zip_path: Path
    warnings: list[str]


class LatexTemplateAgent(BaseAgent):
    content_placeholder = "{{CONTENT}}"
    main_file_candidates = (
        "resume-zh_CN.tex",
        "resume.tex",
        "main.tex",
        "cv.tex",
        "resume_photo.tex",
    )
    system_prompt = (
        "Render verified resume data into a LaTeX resume. Preserve facts and do "
        "not add fictional content."
    )

    def generate(self, resume: ResumeDetail, template_source: str) -> str:
        return self.generate_result(resume, template_source).latex_code

    def generate_package(
        self,
        resume: ResumeDetail,
        template_path: Path,
        output_root: Path,
        package_name: str,
    ) -> LatexPackageResult:
        # The source template directory is read-only here. We copy the whole template
        # package first, then write the generated main .tex only inside the output copy.
        template = self._read_template_tool(template_path)
        package_dir = self._copy_template_to_output_tool(
            template.template_root,
            output_root,
            package_name,
        )
        latex_result = self.generate_result(resume, template.main_template_source)
        relative_main_path = template.main_template_path.relative_to(template.template_root)
        output_main_path = package_dir / relative_main_path
        self._write_file_tool(output_main_path, latex_result.latex_code)
        zip_path = self._zip_package_tool(package_dir)
        return LatexPackageResult(
            latex_code=latex_result.latex_code,
            main_file_name=relative_main_path.as_posix(),
            package_dir=package_dir,
            zip_path=zip_path,
            warnings=latex_result.warnings,
        )

    def generate_result(self, resume: ResumeDetail, template_source: str) -> LatexGenerateResult:
        body = self._render_body(resume)
        latex_code, template_warnings = self._apply_template(template_source, body, resume)
        warnings = self._collect_warnings(resume) + template_warnings
        return LatexGenerateResult(latex_code=latex_code, warnings=warnings)

    def _read_template_tool(self, template_path: Path) -> LatexTemplateReadResult:
        path = template_path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Latex template path not found: {template_path}")

        if path.is_dir():
            template_root = path
            main_template_path = self._find_main_template_file(path)
        else:
            template_root = path.parent
            main_template_path = path

        return LatexTemplateReadResult(
            template_root=template_root,
            main_template_path=main_template_path,
            main_template_source=main_template_path.read_text(encoding="utf-8"),
        )

    def _copy_template_to_output_tool(
        self,
        template_root: Path,
        output_root: Path,
        package_name: str,
    ) -> Path:
        output_root.mkdir(parents=True, exist_ok=True)
        package_dir = output_root / package_name
        if package_dir.exists():
            shutil.rmtree(package_dir)
        shutil.copytree(template_root, package_dir)
        return package_dir

    def _write_file_tool(self, output_path: Path, content: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def _zip_package_tool(self, package_dir: Path) -> Path:
        zip_path = package_dir.with_suffix(".zip")
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(package_dir.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(package_dir))
        return zip_path

    def _find_main_template_file(self, template_dir: Path) -> Path:
        for candidate in self.main_file_candidates:
            path = template_dir / candidate
            if path.exists():
                return path

        for candidate in self.main_file_candidates:
            matches = sorted(template_dir.rglob(candidate))
            if matches:
                return matches[0]

        direct_tex_files = sorted(template_dir.glob("*.tex"))
        if direct_tex_files:
            return direct_tex_files[0]

        nested_tex_files = sorted(template_dir.rglob("*.tex"))
        if nested_tex_files:
            return nested_tex_files[0]

        raise FileNotFoundError(f"No .tex file found in template directory: {template_dir}")

    def _render_body(self, resume: ResumeDetail) -> str:
        sections = [
            self._render_header(resume),
            self._render_section("个人简介", self._render_paragraph(resume.personal_context)),
            self._render_section("教育背景", self._render_educations(resume)),
            self._render_section("专业技能", self._render_itemize(self._split_items(resume.skill_name))),
            self._render_section("项目经历", self._render_projects(resume)),
            self._render_section("实习经历", self._render_interns(resume)),
            self._render_section("获奖情况", self._render_awards(resume)),
        ]
        return "\n\n".join(section for section in sections if section).strip() + "\n"

    def _render_header(self, resume: ResumeDetail) -> str:
        display_name = resume.name or self._non_default_title(resume.title) or "个人简历"
        lines = [
            r"\begin{center}",
            r"{\LARGE\bfseries " + self._escape(display_name) + r"}\\[0.35em]",
        ]
        if resume.expected_position:
            lines.append(r"\textbf{" + self._escape(resume.expected_position) + r"}\\[0.2em]")

        contact_items = [
            resume.phone,
            resume.email,
            f"{resume.age}岁" if resume.age is not None else None,
            f"期望薪资：{resume.expected_salary}" if resume.expected_salary else None,
        ]
        contact_line = " | ".join(item for item in contact_items if item)
        if contact_line:
            lines.append(self._escape(contact_line))
        lines.append(r"\end{center}")
        return "\n".join(lines)

    def _render_educations(self, resume: ResumeDetail) -> str:
        items = []
        for item in resume.educations:
            left = self._join_nonempty([item.university, item.major, item.degree], " | ")
            right = self._date_range(item.start_time, item.end_time)
            items.append(self._render_heading_line(left, right))
        return self._render_itemize(items, already_escaped=True)

    def _render_projects(self, resume: ResumeDetail) -> str:
        blocks = []
        for project in resume.projects:
            heading = self._render_experience_heading(
                project.project_name,
                project.role,
                project.start_time,
                project.end_time,
            )
            lines = [heading]
            if project.introduction:
                lines.append(r"\emph{" + self._escape(project.introduction) + "}")
            bullets = self._split_items(project.content)
            if bullets:
                lines.append(self._render_itemize(bullets))
            blocks.append("\n".join(line for line in lines if line))
        return "\n\n".join(blocks)

    def _render_interns(self, resume: ResumeDetail) -> str:
        blocks = []
        for intern in resume.interns:
            heading = self._render_experience_heading(
                intern.company,
                intern.role,
                intern.start_time,
                intern.end_time,
            )
            bullets = self._split_items(intern.content)
            blocks.append("\n".join([heading, self._render_itemize(bullets)]).strip())
        return "\n\n".join(blocks)

    def _render_awards(self, resume: ResumeDetail) -> str:
        items = []
        for award in resume.awards:
            time_text = self._format_date(award.award_time)
            items.append(self._render_heading_line(award.name, time_text))
        return self._render_itemize(items, already_escaped=True)

    def _render_experience_heading(
        self,
        name: str,
        role: str | None,
        start_time: date | None,
        end_time: date | None,
    ) -> str:
        left = self._escape(name)
        if role:
            left += r" \quad " + self._escape(role)
        right = self._date_range(start_time, end_time)
        if right:
            return r"\textbf{" + left + r"} \hfill " + self._escape(right) + r"\\"
        return r"\textbf{" + left + r"}\\"

    def _render_heading_line(self, left: str, right: str = "") -> str:
        left = self._escape(left)
        if right:
            return r"\textbf{" + left + r"} \hfill " + self._escape(right)
        return r"\textbf{" + left + r"}"

    def _render_section(self, title: str, body: str) -> str:
        if not body:
            return ""
        return r"\section*{" + self._escape(title) + "}\n" + body

    def _render_paragraph(self, value: str | None) -> str:
        value = self._clean_text(value)
        if not value:
            return ""
        return self._escape(value).replace("\n", r"\\ " + "\n")

    def _render_itemize(self, items: list[str], already_escaped: bool = False) -> str:
        cleaned = [item for item in (self._clean_text(item) for item in items) if item]
        if not cleaned:
            return ""
        lines = [r"\begin{itemize}"]
        for item in cleaned:
            lines.append("  " + r"\item " + (item if already_escaped else self._escape(item)))
        lines.append(r"\end{itemize}")
        return "\n".join(lines)

    def _split_items(self, value: str | None) -> list[str]:
        value = self._clean_text(value)
        if not value:
            return []

        items: list[str] = []
        for line in value.splitlines():
            line = self._clean_text(line)
            if not line:
                continue
            parts = re.split(r"(?=\d+[.、]\s*)", line)
            if len(parts) > 1:
                items.extend(self._clean_text(part) for part in parts if self._clean_text(part))
            else:
                items.append(line)

        if len(items) == 1:
            split_items = [
                self._clean_text(part)
                for part in re.split(r"[；;]\s*", items[0])
                if self._clean_text(part)
            ]
            if len(split_items) > 1:
                return split_items
        return items

    def _apply_template(
        self,
        template_source: str,
        body: str,
        resume: ResumeDetail,
    ) -> tuple[str, list[str]]:
        warnings: list[str] = []
        template = template_source.strip() or self._default_template()
        if self.content_placeholder in template:
            return template.replace(self.content_placeholder, body), warnings
        if not self.should_use_mock():
            try:
                return self._adapt_template_with_llm(template, body, resume), warnings
            except Exception as exc:
                if not self.allow_fallback:
                    raise
                warnings.append(f"LaTeX 模板 Agent 调用失败，已使用本地兜底渲染：{exc}")
        elif not self.allow_fallback:
            self.raise_real_llm_required()
        if r"\begin{document}" in template and r"\end{document}" in template:
            warnings.append("模板缺少 {{CONTENT}} 占位符，已保留导言区并重写正文内容。")
            return self._replace_document_body(template, body), warnings
        warnings.append("模板不是完整 LaTeX 文档，已使用内置默认模板包裹内容。")
        return self._default_template().replace(self.content_placeholder, body), warnings

    def _replace_document_body(self, template_source: str, body: str) -> str:
        begin_token = r"\begin{document}"
        end_token = r"\end{document}"
        begin_index = template_source.find(begin_token)
        end_index = template_source.rfind(end_token)
        if begin_index < 0 or end_index < begin_index:
            return self._default_template().replace(self.content_placeholder, body)
        preamble = template_source[: begin_index + len(begin_token)].rstrip()
        ending = template_source[end_index:].strip()
        return f"{preamble}\n{body.rstrip()}\n{ending}\n"

    def _adapt_template_with_llm(
        self,
        template_source: str,
        rendered_body: str,
        resume: ResumeDetail,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a LaTeX resume template adapter. Read the provided "
                        "LaTeX template source and replace its sample resume content "
                        "with the verified resume data. Preserve the template's "
                        "documentclass, packages, custom commands, layout style, "
                        "fonts, images, and macros whenever possible. Do not invent "
                        "facts. Return one complete compilable .tex file only. "
                        "Do not wrap the answer in markdown fences."
                    ),
                ),
                (
                    "human",
                    (
                        "Template source:\n{template_source}\n\n"
                        "Resume JSON:\n{resume_json}\n\n"
                        "Canonical rendered resume body you may reuse if helpful:\n"
                        "{rendered_body}\n\n"
                        "Return only complete LaTeX code."
                    ),
                ),
            ]
        )
        chain = prompt | self.build_llm(temperature=0)
        response = self.invoke_with_retries(
            chain,
            {
                "template_source": template_source[:30000],
                "resume_json": resume.model_dump_json(by_alias=True),
                "rendered_body": rendered_body[:12000],
            },
        )
        return self._strip_latex_response(response.content)

    def _strip_latex_response(self, content: object) -> str:
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        raw = str(content).strip()
        raw = re.sub(r"^```(?:latex|tex)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        return raw.strip()

    def _collect_warnings(self, resume: ResumeDetail) -> list[str]:
        warnings = []
        if not (resume.name or self._non_default_title(resume.title)):
            warnings.append("简历缺少姓名或有效标题。")
        if not resume.skill_name:
            warnings.append("简历缺少专业技能内容。")
        if not resume.educations:
            warnings.append("简历缺少教育背景。")
        if not resume.projects and not resume.interns:
            warnings.append("简历缺少项目或实习经历。")
        return warnings

    def _default_template(self) -> str:
        return (
            "\\documentclass[11pt]{article}\n"
            "\\usepackage[UTF8]{ctex}\n"
            "\\usepackage[a4paper,margin=1.7cm]{geometry}\n"
            "\\usepackage{enumitem}\n"
            "\\usepackage{titlesec}\n"
            "\\pagestyle{empty}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlist[itemize]{leftmargin=1.6em,itemsep=0.2em,topsep=0.2em}\n"
            "\\titleformat{\\section}{\\large\\bfseries}{}{0em}{}[\\titlerule]\n"
            "\\begin{document}\n"
            "{{CONTENT}}\n"
            "\\end{document}\n"
        )

    def _date_range(self, start_time: date | None, end_time: date | None) -> str:
        start = self._format_date(start_time)
        end = self._format_date(end_time)
        if start and end:
            return f"{start} - {end}"
        if start:
            return f"{start} - 至今"
        if end:
            return f"截至 {end}"
        return ""

    def _format_date(self, value: date | datetime | str | None) -> str:
        if not value:
            return ""
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return f"{value.year}.{value.month:02d}"
        match = re.search(r"(\d{4})[-./年](\d{1,2})?", str(value))
        if match:
            month = match.group(2)
            return f"{match.group(1)}.{int(month):02d}" if month else match.group(1)
        return str(value)

    def _non_default_title(self, title: str | None) -> str:
        title = self._clean_text(title)
        return "" if title == "PDF imported resume" else title

    def _join_nonempty(self, values: list[str | None], separator: str) -> str:
        return separator.join(self._clean_text(value) for value in values if self._clean_text(value))

    def _clean_text(self, value: str | None) -> str:
        if value is None:
            return ""
        value = str(value).replace("\uf06c", "")
        value = re.sub(r"\r\n?", "\n", value)
        value = re.sub(r"[ \t]+", " ", value)
        return value.strip(" \n\t·•●○▪▫*-+")

    def _escape(self, value: str | None) -> str:
        text = self._clean_text(value)
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(char, char) for char in text)
