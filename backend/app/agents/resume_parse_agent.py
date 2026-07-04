import json
import re
from datetime import date
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.agents.base import BaseAgent
from app.schemas.resume import AwardInput, EducationInput, ProjectInput, StandardResume


class ResumeParseAgent(BaseAgent):
    system_prompt = (
        "You are a resume parsing agent. Extract one JSON object matching the schema. "
        "Return valid JSON only, without markdown fences or explanations. "
        "Only use facts present in the resume text. Do not invent experience, dates, "
        "salary, age, company names, or metrics. Missing scalar fields must be null, "
        "and missing list fields must be empty arrays. "
        "Map resume labels carefully: 姓名/name/top header -> name; 年龄 -> age; "
        "邮箱/email -> email; 手机/电话/tel -> phone; 求职意向/期望岗位/应聘岗位 -> "
        "expectedPosition; 期望薪资/薪资要求 -> expectedSalary. "
        "Keep project and internship entries even when role, startTime, or endTime is "
        "missing; set only the missing fields to null. Do not drop a project just "
        "because no date is present. "
        "For dates, normalize YYYY.MM or YYYY-MM to the first day of that month. "
        "If the text says 至今/current/present and no explicit end date is available, "
        "use null. If an expected graduation date is present, it may be used as the "
        "education endTime. Use skillName as a comma-separated list of technical skills."
    )

    def parse(self, pdf_text: str) -> StandardResume:
        if self.should_use_mock():
            if not self.allow_fallback:
                self.raise_real_llm_required()
            return self._mock_parse(pdf_text)

        schema = json.dumps(
            StandardResume.model_json_schema(by_alias=True),
            ensure_ascii=False,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                (
                    "human",
                    "JSON schema:\n{schema}\n\nResume text:\n{text}",
                ),
            ]
        )
        chain = prompt | self.build_llm(temperature=0)
        try:
            response = self.invoke_with_retries(
                chain,
                {
                    "schema": schema,
                    "text": self._normalize_text(pdf_text)[:12000],
                },
            )
            resume = StandardResume.model_validate(self._load_json_object(response.content))
            return self._finalize_resume(resume, pdf_text)
        except Exception:
            if not self.allow_fallback:
                raise
            return self._mock_parse(pdf_text)

    def _mock_parse(self, pdf_text: str) -> StandardResume:
        text = self._normalize_text(pdf_text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        name = self._extract_name(lines)
        expected_position = self._extract_position(text)
        title = self._build_title(name, expected_position, lines)
        personal_context = "\n".join(lines[:8]) if lines else "Pending manual check."
        return StandardResume(
            title=title,
            name=name,
            age=self._extract_age(text),
            email=self._extract_email(text),
            phone=self._extract_phone(text),
            expected_salary=self._extract_labeled_value(
                text,
                ("期望薪资", "薪资要求", "期望工资"),
            ),
            expected_position=expected_position,
            skill_name=self._extract_skill_text(text),
            personal_context=personal_context,
            status="DRAFT",
            educations=self._extract_mock_educations(text),
            projects=self._extract_mock_projects(text),
            interns=[],
            awards=self._extract_mock_awards(text),
        )

    def _finalize_resume(self, resume: StandardResume, pdf_text: str) -> StandardResume:
        text = self._normalize_text(pdf_text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        extracted_name = self._extract_name(lines)
        if extracted_name and (not resume.name or self._looks_like_bad_name(resume.name)):
            resume.name = extracted_name
        if not resume.age:
            resume.age = self._extract_age(text)
        if not resume.email:
            resume.email = self._extract_email(text)
        if not resume.phone:
            resume.phone = self._extract_phone(text)
        extracted_position = self._extract_position(text)
        if extracted_position and (
            not resume.expected_position
            or self._looks_like_bad_position(resume.expected_position)
        ):
            resume.expected_position = extracted_position
        if not resume.expected_salary:
            resume.expected_salary = self._extract_labeled_value(
                text,
                ("期望薪资", "薪资要求", "期望工资"),
            )
        if not resume.skill_name:
            resume.skill_name = self._extract_skill_text(text)
        if not resume.educations:
            resume.educations = self._extract_mock_educations(text)
        if not resume.projects:
            resume.projects = self._extract_mock_projects(text)
        if not resume.awards:
            resume.awards = self._extract_mock_awards(text)
        if not resume.personal_context:
            resume.personal_context = "\n".join(lines[:8]) if lines else ""
        if self._looks_like_bad_title(resume.title):
            resume.title = self._build_title(resume.name, resume.expected_position, lines)
        return resume

    def _extract_position(self, text: str) -> str | None:
        value = self._extract_labeled_value(
            text,
            ("求职意向", "期望岗位", "应聘岗位", "求职岗位"),
        )
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not value and lines and self._looks_like_position_line(lines[0]):
            value = lines[0]
        return None if self._looks_like_bad_position(value) else value

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"([A-Za-z])\n([A-Za-z])", r"\1\2", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _load_json_object(self, content: Any) -> dict[str, Any]:
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        raw = str(content).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start < 0 or end < start:
                raise
            payload = json.loads(raw[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("Resume parse agent must return a JSON object.")
        return payload

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(
            r"(?:\+?86[\s\-()（）]*)?1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}",
            text,
        )
        if not match:
            return None
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("86") and len(digits) == 13:
            digits = digits[2:]
        return digits if len(digits) == 11 else match.group(0).strip()

    def _extract_age(self, text: str) -> int | None:
        match = re.search(r"(?<!\d)(1[6-9]|[2-5]\d|60)\s*岁", text)
        return int(match.group(1)) if match else None

    def _extract_name(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines[:80]):
            if line in {"姓名", "姓 名"}:
                value = self._next_value(lines, index + 1, self._is_name_candidate)
                if value:
                    return value
            if line == "姓" and index + 1 < len(lines) and lines[index + 1] == "名":
                value = self._next_value(lines, index + 2, self._is_name_candidate)
                if value:
                    return value

        for line in lines[:80]:
            value = line.strip(" ·•|,，")
            if self._is_name_candidate(value):
                return value
        return None

    def _extract_labeled_value(self, text: str, labels: tuple[str, ...]) -> str | None:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(
            rf"(?:{label_pattern})\s*[:：]\s*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if match:
            value = self._clean_labeled_value(match.group(1))
            if value:
                return value

        for index, line in enumerate(lines):
            for label in labels:
                compact_line = re.sub(r"\s+", "", line)
                compact_label = re.sub(r"\s+", "", label)
                if compact_line == compact_label:
                    value = self._next_value(lines, index + 1)
                    if value:
                        return value
                if compact_line.startswith(compact_label):
                    value = self._clean_labeled_value(line[len(label) :])
                    if value:
                        return value
                if len(label) == 2 and line == label[0] and index + 1 < len(lines):
                    if lines[index + 1] == label[1]:
                        value = self._next_value(lines, index + 2)
                        if value:
                            return value
        return None

    def _extract_skill_text(self, text: str) -> str:
        section = self._section(
            text,
            ("IT技能", "专业技能", "技能特长", "技能"),
            ("自我评价", "项目经历", "项目经验", "实习经历", "获奖"),
        )
        if not section:
            return ""
        lines = [line.strip(" ·•") for line in section.splitlines() if line.strip()]
        return "；".join(lines)[:2000]

    def _extract_mock_educations(self, text: str) -> list[EducationInput]:
        section = self._section(
            text,
            ("教育背景", "教育经历"),
            ("项目经历", "项目经验", "实习经历", "工作经历", "技能特长", "专业技能", "技能"),
        )
        if not section:
            return []

        lines = [line.strip(" ·•") for line in section.splitlines() if line.strip()]
        date_index: int | None = None
        start_time: date | None = None
        end_time: date | None = None
        for index, line in enumerate(lines[:5]):
            parsed_start, parsed_end = self._parse_date_range(line)
            if parsed_start:
                start_time = parsed_start
                end_time = parsed_end
                date_index = index
                break
        if not start_time:
            return []

        remaining = [
            line
            for index, line in enumerate(lines)
            if index != date_index and not line.startswith("主修课程")
        ]
        university = next((line for line in remaining if re.search(r"(大学|学院|学校)", line)), None)
        major_line = next(
            (
                line
                for line in remaining
                if line != university and re.search(r"(本科|硕士|博士|专科|学士|专业)", line)
            ),
            None,
        )
        if not university and remaining:
            university = remaining[0]
        if not major_line:
            major_line = next((line for line in remaining if line != university), "")

        major, degree = self._split_major_degree(major_line)
        if not university or not major:
            return []
        return [
            EducationInput(
                university=university[:100],
                major=major[:100],
                degree=degree[:30],
                start_time=start_time,
                end_time=end_time,
            )
        ]

    def _extract_mock_projects(self, text: str) -> list[ProjectInput]:
        section = self._section(
            text,
            ("项目经历", "项目经验"),
            ("实习经历", "工作经历", "获奖", "奖项", "教育背景", "技能特长", "专业技能", "技能", "自我评价"),
        )
        if not section:
            return []

        projects: list[ProjectInput] = []
        current_name: str | None = None
        current_role: str | None = None
        current_lines: list[str] = []

        for raw_line in section.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self._looks_like_project_heading(line):
                if current_name:
                    projects.append(
                        ProjectInput(
                            project_name=current_name[:100],
                            role=current_role,
                            introduction=current_lines[0] if current_lines else None,
                            content="\n".join(current_lines),
                        )
                    )
                current_name, current_role = self._split_project_heading(line)
                current_lines = []
            elif current_name:
                current_lines.append(line)

        if current_name:
            projects.append(
                ProjectInput(
                    project_name=current_name[:100],
                    role=current_role,
                    introduction=current_lines[0] if current_lines else None,
                    content="\n".join(current_lines),
                )
            )
        return projects

    def _extract_mock_awards(self, text: str) -> list[AwardInput]:
        section = self._section(text, ("获奖情况", "获奖经历", "奖项"), ("项目经历", "项目经验", "实习经历", "工作经历"))
        if not section:
            return []
        awards: list[AwardInput] = []
        pending_name: str | None = None
        for raw_line in section.splitlines():
            line = raw_line.strip(" +·•")
            if not line:
                continue
            year_match = re.fullmatch(r"(20\d{2})年?", line)
            if year_match and pending_name:
                awards.append(AwardInput(name=pending_name[:150], award_time=f"{year_match.group(1)}-01-01"))
                pending_name = None
            elif not re.search(r"获奖|奖项", line):
                if pending_name:
                    awards.append(AwardInput(name=pending_name[:150]))
                pending_name = line
        if pending_name:
            awards.append(AwardInput(name=pending_name[:150]))
        return awards

    def _section(
        self,
        text: str,
        start_labels: tuple[str, ...],
        end_labels: tuple[str, ...],
    ) -> str:
        start_pattern = "|".join(re.escape(label) for label in start_labels)
        start = re.search(rf"(?:^|\n)\s*[+·•-]*\s*(?:{start_pattern})\s*(?:\n|$)", text)
        if not start:
            return ""
        rest = text[start.end() :]
        end_pattern = "|".join(re.escape(label) for label in end_labels)
        end = re.search(rf"(?:^|\n)\s*[+·•-]*\s*(?:{end_pattern})\s*(?:\n|$)", rest)
        return rest[: end.start()] if end else rest

    def _looks_like_project_heading(self, line: str) -> bool:
        if len(line) > 120:
            return False
        if re.match(r"^\d+[.、]", line) or line.endswith(("。", "，", "；", ";", ",")):
            return False
        if re.search(r"[:：]|技术栈|负责|基于|使用|支持|提升|降低|实现", line):
            return False
        return bool(
            re.search(
                r"(项目|平台|系统|网站|小程序|APP|App|Agent|服务|分析|测试|预测|建模|画像|推荐|优化)",
                line,
            )
        )

    def _split_project_heading(self, line: str) -> tuple[str, str | None]:
        line = re.split(r"\[|在线演示|后端源码", line, maxsplit=1)[0].strip(" -－—|")
        parts = re.split(r"[－—-]", line, maxsplit=1)
        if len(parts) == 2 and len(parts[1].strip()) <= 30:
            return parts[0].strip(), parts[1].strip()
        return line, None

    def _build_title(
        self,
        name: str | None,
        expected_position: str | None,
        lines: list[str],
    ) -> str:
        if name and expected_position:
            return f"{name}-{expected_position}"[:100]
        if name:
            return f"{name}的简历"[:100]
        return lines[0][:100] if lines else "PDF imported resume"

    def _looks_like_position_line(self, line: str) -> bool:
        if self._extract_email(line) or self._extract_phone(line):
            return False
        if self._extract_name([line]):
            return False
        return bool(
            re.search(
                r"(开发|工程师|实习|算法|前端|后端|全栈|测试|产品|运营|Agent|AI|数据|分析师|研究员)",
                line,
            )
        )

    def _is_name_candidate(self, value: str | None) -> bool:
        if not value:
            return False
        value = value.strip(" ·•|,，")
        if self._looks_like_bad_name(value):
            return False
        if self._extract_email(value) or self._extract_phone(value):
            return False
        if value.upper() in {"M", "F"} or value in {"男", "女"}:
            return False
        chinese_name = re.fullmatch(r"[\u4e00-\u9fff]{2,6}", value)
        english_name = re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,40}", value)
        return bool(chinese_name or english_name)

    def _looks_like_bad_name(self, value: str | None) -> bool:
        if not value:
            return True
        compact = re.sub(r"\s+", "", value).lower()
        bad_exact = {
            "个人简历",
            "简历",
            "个人信息",
            "基本信息",
            "求职意向",
            "教育背景",
            "教育经历",
            "项目经历",
            "项目经验",
            "技能特长",
            "专业技能",
            "自我评价",
            "personalresume",
            "resume",
        }
        if compact in bad_exact:
            return True
        return bool(
            re.search(
                r"(简历|求职|意向|岗位|电话|手机|邮箱|年龄|性别|教育|技能|项目|经历|背景|课程|personal|resume)",
                compact,
            )
        )

    def _looks_like_bad_position(self, value: str | None) -> bool:
        if not value:
            return True
        compact = re.sub(r"\s+", "", value).lower()
        if compact in {"个人简历", "简历", "基本信息", "求职意向", "personalresume", "resume"}:
            return True
        return bool(re.search(r"(电话|手机|邮箱|年龄|性别|教育背景|项目经历|技能特长)", compact))

    def _looks_like_bad_title(self, value: str | None) -> bool:
        if not value or value == "PDF imported resume":
            return True
        if "个人简历" in value or "PDF imported resume" in value:
            return True
        return False

    def _next_value(
        self,
        lines: list[str],
        start_index: int,
        predicate: Any | None = None,
    ) -> str | None:
        for line in lines[start_index : start_index + 6]:
            value = self._clean_labeled_value(line)
            if not value:
                continue
            if self._looks_like_standalone_label(value):
                continue
            if predicate and not predicate(value):
                continue
            return value
        return None

    def _clean_labeled_value(self, value: str) -> str | None:
        cleaned = value.strip(" \t·•|,，;；:-：")
        return cleaned or None

    def _looks_like_standalone_label(self, value: str) -> bool:
        compact = re.sub(r"\s+", "", value)
        labels = {
            "姓",
            "名",
            "姓名",
            "年龄",
            "性",
            "别",
            "性别",
            "电话",
            "手机",
            "邮",
            "箱",
            "邮箱",
            "求职意向",
            "期望岗位",
            "教育背景",
            "项目经历",
            "技能特长",
            "自我评价",
        }
        return compact in labels

    def _parse_date_range(self, value: str) -> tuple[date | None, date | None]:
        parts = re.findall(r"(20\d{2})[./年-]?(\d{1,2})?", value)
        if not parts:
            return None, None
        start = self._make_month_date(parts[0])
        end = None
        if len(parts) >= 2 and not re.search(r"(至今|现在|present|current)", value, re.I):
            end = self._make_month_date(parts[1])
        return start, end

    def _make_month_date(self, item: tuple[str, str]) -> date:
        year = int(item[0])
        month = int(item[1] or "1")
        month = min(max(month, 1), 12)
        return date(year, month, 1)

    def _split_major_degree(self, value: str) -> tuple[str, str]:
        cleaned = value.strip(" ·•|,，;；")
        degree = "本科"
        degree_match = re.search(r"[（(]?\s*(本科|硕士|博士|专科|学士)\s*[）)]?", cleaned)
        if degree_match:
            degree = degree_match.group(1)
            cleaned = re.sub(r"[（(]?\s*(本科|硕士|博士|专科|学士)\s*[）)]?", "", cleaned).strip()
        cleaned = cleaned.replace("专业", "").strip(" ·•|,，;；")
        return cleaned, degree
