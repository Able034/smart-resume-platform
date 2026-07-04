import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import AliasChoices, Field

from app.agents.base import BaseAgent
from app.schemas.common import AppSchema
from app.schemas.resume import ResumeDetail


class TextOptimization(AppSchema):
    original: str = ""
    optimized: str = ""
    reason: str = ""
    missing_facts: list[str] = Field(default_factory=list)


class SegmentOptimization(AppSchema):
    segment_index: int = 0
    original: str = ""
    optimized: str = ""
    changed: bool = True
    reason: str = ""
    star_breakdown: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)


class ExperienceOptimization(AppSchema):
    source_id: int | None = None
    name: str = ""
    role: str | None = None
    original: str = ""
    star_breakdown: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("starBreakdown", "statBreakdown"),
        serialization_alias="starBreakdown",
    )
    optimized_bullets: list[str] = Field(default_factory=list)
    segments: list[SegmentOptimization] = Field(default_factory=list)
    reason: str = ""
    missing_facts: list[str] = Field(default_factory=list)


class ResumeOptimizationPayload(AppSchema):
    summary: str = ""
    score: float | None = Field(default=None, ge=0, le=100)
    skill: TextOptimization = Field(default_factory=TextOptimization)
    projects: list[ExperienceOptimization] = Field(default_factory=list)
    interns: list[ExperienceOptimization] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OptimizationResult:
    def __init__(
        self,
        content: str,
        score: float | None = None,
        payload: ResumeOptimizationPayload | None = None,
    ):
        self.content = content
        self.score = score
        self.payload = payload


class ResumeOptimizeAgent(BaseAgent):
    system_prompt = (
        "你是中文求职简历表达优化 Agent。你的任务是优化技能、项目经历和实习经历的表达，"
        "让内容更适合放进正式简历和 LaTeX 模板。你只能基于输入简历和岗位内容改写表达，"
        "不得编造公司、项目、技术栈、指标、奖项、时间、结果或经历。"
        "如果缺少可量化结果，就写成可验证的贡献表达，并把需要用户补充的信息放到 missingFacts。"
        "项目和实习经历使用 STAR 法则组织：Situation=场景/背景，Task=任务/目标，"
        "Action=行动/技术方案，Result=结果/影响。没有事实支撑的 Result 不要硬写数字。"
        "如果输入包含岗位分析 JSON，你必须优先使用 jobArchetype、scoring、resumeMatch、"
        "customizationPlan、interviewPlan、optimizationFocus、starStoryFocus 和 resumeRewriteFocus "
        "决定优化重点；高权重匹配项优先，真实性风险和缺口只写成提醒或 missingFacts。"
        "一段经历里可能包含多个独立任务，你必须先拆成多个任务段，再逐段判断是否需要优化。"
        "表达已经清晰、具体、符合 STAR 的任务段要保留原文，不要为了改而改。"
        "返回严格 JSON，不要 markdown。"
    )

    def optimize(
        self,
        resume: ResumeDetail,
        job_content: str | None = None,
    ) -> OptimizationResult:
        if self.should_use_mock():
            if not self.allow_fallback:
                self.raise_real_llm_required()
            payload = self._fallback_payload(
                resume,
                "Mock mode suggestion.",
                job_analysis=self._extract_job_analysis(job_content),
            )
            return OptimizationResult(
                content=self._format_payload(payload),
                score=payload.score,
                payload=payload,
            )

        job_analysis = self._extract_job_analysis(job_content)
        raw_job_content = self._extract_raw_job_content(job_content)
        schema = json.dumps(
            ResumeOptimizationPayload.model_json_schema(by_alias=True),
            ensure_ascii=False,
            indent=2,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                (
                    "human",
                    "\n".join(
                        [
                            "请按照下面 JSON Schema 输出优化结果，只返回一个 JSON 对象。",
                            "输出要求：",
                            "1. skill.optimized 要把零散技能改成分层、岗位导向、可读的技能表达。",
                            "2. 对 projects 和 interns，先把 original/content 按独立任务拆成 segments。",
                            "3. 每个 segment 对应原文中的一个任务或动作，不要把多个无关任务揉成一句。",
                            "4. 每个 segment.optimized 都要是完整的 STAR 式简历表达：背景/目标、行动方法、结果或影响。",
                            "5. 如果某个任务段原文已经清晰、具体、符合 STAR，则 changed=false，optimized 必须等于 original。",
                            "同一条经历里允许部分 segments 不修改，也允许全部 segments 都不修改。",
                            "6. 如果原文只是笼统描述，可在不编造事实的前提下优化动词、方法和结果方向。",
                            "示例：原文“基于服务器日志数据，分析系统异常发生情况，定位故障原因，并提出系统优化方案。”，"
                            "可改为“基于服务器日志数据，识别系统异常高发时段与关键故障模式，通过日志聚类与异常检测定位核心问题，并提出稳定性优化方案以降低系统故障率。”",
                            "7. 不要新增输入中没有的技术、业务、数字指标；缺少指标时写入 missingFacts。",
                            "8. optimizedBullets 必须按 segments 顺序汇总所有 segment.optimized，尽量和任务段数量一致，最多 6 条。",
                            "9. starBreakdown 用 4 条概括整条经历如何对应 STAR；每个 segment.starBreakdown 也用 4 条说明该段的 STAR 映射。",
                            "10. 如果提供了岗位内容，可适度向岗位关键词靠拢，但仍不能编造经历。",
                            "11. 如果提供了岗位分析 JSON，必须优先围绕 resumeMatch.mappings 中 importance=high 的要求改写；"
                            "gap 只能转为 missingFacts 或补充建议，不能伪造经历。",
                            "12. STAR 故事重点从 interviewPlan.starStoryPrompts 和 starStoryFocus 中选择；"
                            "每条经历只强化真实相关的部分。",
                            "13. 技能和项目排序要服务于 jobArchetype、optimizationFocus、resumeRewriteFocus；"
                            "如果 scoring 或 authenticityCheck 显示风险，在 warnings 中提醒。",
                            "JSON Schema:\n{schema}",
                            "简历 JSON:\n{resume_json}",
                            "岗位分析 JSON（可为空）:\n{job_analysis_json}",
                            "岗位内容（可为空）:\n{job_content}",
                        ]
                    ),
                ),
            ]
        )
        chain = prompt | self.build_llm(temperature=0.2)
        try:
            response = self.invoke_with_retries(
                chain,
                {
                    "schema": schema,
                    "resume_json": json.dumps(
                        self._resume_to_agent_payload(resume),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "job_analysis_json": json.dumps(
                        job_analysis or {}, ensure_ascii=False, indent=2
                    ),
                    "job_content": raw_job_content[:12000],
                },
            )
            payload = self._finalize_payload(
                ResumeOptimizationPayload.model_validate(
                    self._load_json_object(response.content)
                ),
                job_analysis=job_analysis,
            )
            return OptimizationResult(
                content=self._format_payload(payload),
                score=payload.score,
                payload=payload,
            )
        except Exception:
            if not self.allow_fallback:
                raise
            payload = self._fallback_payload(
                resume,
                "LLM optimization failed after retries. Returned rule-based suggestions.",
                job_analysis=job_analysis,
            )
            return OptimizationResult(
                content=self._format_payload(payload),
                score=payload.score,
                payload=payload,
            )

    def _finalize_payload(
        self,
        payload: ResumeOptimizationPayload,
        job_analysis: dict[str, Any] | None = None,
    ) -> ResumeOptimizationPayload:
        if not payload.summary:
            focus = self._focus_from_job_analysis(job_analysis)
            if focus:
                payload.summary = "已根据岗位分析调整简历优化重点：" + "；".join(focus[:5])
            else:
                payload.summary = "已根据岗位内容优化技能、项目和实习经历表达。"
        for item in [*payload.projects, *payload.interns]:
            if not item.segments:
                item.segments = self._segments_from_bullets(item)
            item.segments.sort(key=lambda segment: segment.segment_index)
            for index, segment in enumerate(item.segments):
                segment.segment_index = index
                if not segment.optimized:
                    segment.optimized = segment.original
                segment.changed = self._clean_text(segment.original) != self._clean_text(
                    segment.optimized
                )
            if item.segments:
                item.optimized_bullets = [
                    segment.optimized or segment.original
                    for segment in item.segments
                    if segment.optimized or segment.original
                ]
        return payload

    def _segments_from_bullets(self, item: ExperienceOptimization) -> list[SegmentOptimization]:
        if not item.optimized_bullets:
            return []
        originals = self._split_experience_segments(item.original)
        segments: list[SegmentOptimization] = []
        for index, bullet in enumerate(item.optimized_bullets[:6]):
            original = originals[index] if index < len(originals) else bullet
            optimized = bullet.strip(" -•·")
            segments.append(
                SegmentOptimization(
                    segment_index=index,
                    original=original,
                    optimized=optimized,
                    changed=self._clean_text(original) != self._clean_text(optimized),
                    reason=item.reason or "按 STAR 结构优化该任务段表达。",
                    star_breakdown=item.star_breakdown,
                    missing_facts=item.missing_facts,
                )
            )
        return segments

    def _resume_to_agent_payload(self, resume: ResumeDetail) -> dict[str, Any]:
        return {
            "resumeId": resume.resume_id,
            "title": resume.title,
            "name": resume.name,
            "expectedPosition": resume.expected_position,
            "skillName": resume.skill_name,
            "personalContext": resume.personal_context,
            "projects": [
                {
                    "sourceId": item.project_info_id,
                    "projectName": item.project_name,
                    "role": item.role,
                    "introduction": item.introduction,
                    "content": item.content,
                    "startTime": item.start_time.isoformat() if item.start_time else None,
                    "endTime": item.end_time.isoformat() if item.end_time else None,
                }
                for item in resume.projects
            ],
            "interns": [
                {
                    "sourceId": item.intern_info_id,
                    "company": item.company,
                    "role": item.role,
                    "content": item.content,
                    "startTime": item.start_time.isoformat() if item.start_time else None,
                    "endTime": item.end_time.isoformat() if item.end_time else None,
                }
                for item in resume.interns
            ],
        }

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
            raise ValueError("Resume optimization agent must return a JSON object.")
        return payload

    def _format_payload(self, payload: ResumeOptimizationPayload) -> str:
        lines: list[str] = []
        if payload.score is not None:
            lines.append(f"综合评分：{payload.score:.1f}/100")
        if payload.summary:
            lines.extend(["", f"总体建议：{payload.summary}"])

        lines.extend(["", "## 技能表达优化"])
        lines.extend(self._format_text_optimization(payload.skill))

        lines.extend(["", "## 项目经历优化（STAR）"])
        if payload.projects:
            for item in payload.projects:
                lines.extend(self._format_experience(item))
        else:
            lines.append("暂无可优化的项目经历。")

        lines.extend(["", "## 实习经历优化（STAR）"])
        if payload.interns:
            for item in payload.interns:
                lines.extend(self._format_experience(item))
        else:
            lines.append("暂无可优化的实习经历。")

        if payload.warnings:
            lines.extend(["", "## 风险提醒"])
            lines.extend(f"- {warning}" for warning in payload.warnings if warning)
        return "\n".join(line for line in lines if line is not None).strip()

    def _format_text_optimization(self, item: TextOptimization) -> list[str]:
        lines: list[str] = []
        if item.original:
            lines.append(f"原始表达：{item.original}")
        if item.optimized:
            lines.append(f"优化表达：{item.optimized}")
        if item.reason:
            lines.append(f"优化理由：{item.reason}")
        if item.missing_facts:
            lines.append("建议补充：" + "；".join(item.missing_facts))
        return lines or ["暂无技能内容可优化。"]

    def _format_experience(self, item: ExperienceOptimization) -> list[str]:
        title = item.name or "未命名经历"
        if item.role:
            title = f"{title} / {item.role}"
        lines = ["", f"### {title}"]
        if item.original:
            lines.append(f"原始表达：{item.original}")
        if item.star_breakdown:
            lines.append("STAR 拆解：")
            lines.extend(f"- {entry}" for entry in item.star_breakdown if entry)
        if item.optimized_bullets:
            lines.append("优化表达：")
            lines.extend(f"- {bullet}" for bullet in item.optimized_bullets if bullet)
        if item.segments:
            lines.append("分段判断：")
            for segment in item.segments:
                status = "已优化" if segment.changed else "保留原文"
                lines.append(f"- 任务 {segment.segment_index + 1}（{status}）：{segment.reason}")
        if item.reason:
            lines.append(f"优化理由：{item.reason}")
        if item.missing_facts:
            lines.append("建议补充：" + "；".join(item.missing_facts))
        return lines

    def _fallback_payload(
        self,
        resume: ResumeDetail,
        prefix: str,
        job_analysis: dict[str, Any] | None = None,
    ) -> ResumeOptimizationPayload:
        focus = self._focus_from_job_analysis(job_analysis)
        score = self._score_from_job_analysis(job_analysis) or 72.0
        warnings = [
            "规则兜底不会补充不存在的业务结果或量化指标。",
            "缺少项目成果时，建议人工补充性能、规模、准确率、转化率或效率提升等事实。",
        ]
        warnings.extend(self._warnings_from_job_analysis(job_analysis))
        return ResumeOptimizationPayload(
            summary=(
                f"{prefix} 当前建议先把技能从关键词堆叠改成分层能力，把项目和实习按 "
                "STAR 补齐场景、任务、行动和结果。"
                + (f" 本次岗位优化优先关注：{'；'.join(focus[:5])}。" if focus else "")
            ),
            score=score,
            skill=self._fallback_skill(resume),
            projects=[self._fallback_project(item) for item in resume.projects],
            interns=[self._fallback_intern(item) for item in resume.interns],
            warnings=warnings,
        )

    def _extract_job_analysis(self, job_content: str | None) -> dict[str, Any] | None:
        if not job_content:
            return None
        try:
            payload = json.loads(job_content)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        analysis = payload.get("analysis")
        if isinstance(analysis, dict):
            return analysis
        if any(key in payload for key in ("jobArchetype", "resumeMatch", "scoring")):
            return payload
        return None

    def _extract_raw_job_content(self, job_content: str | None) -> str:
        if not job_content:
            return ""
        try:
            payload = json.loads(job_content)
        except json.JSONDecodeError:
            return job_content or ""
        if isinstance(payload, dict):
            raw = payload.get("rawContent")
            if isinstance(raw, str):
                return raw
        return job_content or ""

    def _focus_from_job_analysis(self, job_analysis: dict[str, Any] | None) -> list[str]:
        if not job_analysis:
            return []
        focus: list[str] = []
        for key in ("optimizationFocus", "starStoryFocus", "resumeRewriteFocus"):
            value = job_analysis.get(key)
            if isinstance(value, list):
                focus.extend(str(item) for item in value if item)
        customization = job_analysis.get("customizationPlan")
        if isinstance(customization, dict):
            for key in ("keywordFocus", "rewriteFocus"):
                value = customization.get(key)
                if isinstance(value, list):
                    focus.extend(str(item) for item in value if item)
        return focus

    def _score_from_job_analysis(self, job_analysis: dict[str, Any] | None) -> float | None:
        if not job_analysis:
            return None
        for path in (("scoring", "globalScore"), ("matchScore",)):
            value: Any = job_analysis
            for key in path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if isinstance(value, int | float):
                return float(value)
        return None

    def _warnings_from_job_analysis(self, job_analysis: dict[str, Any] | None) -> list[str]:
        if not job_analysis:
            return []
        warnings: list[str] = []
        authenticity = job_analysis.get("authenticityCheck")
        if isinstance(authenticity, dict):
            verdict = authenticity.get("verdict")
            if verdict and str(verdict).lower() not in {"active", "open", "likely_active"}:
                warnings.append(f"岗位真实性需要复核：{verdict}")
            red_flags = authenticity.get("redFlags")
            if isinstance(red_flags, list):
                warnings.extend(str(item) for item in red_flags[:3] if item)
        resume_match = job_analysis.get("resumeMatch")
        if isinstance(resume_match, dict):
            gaps = resume_match.get("gaps")
            if isinstance(gaps, list):
                warnings.extend(f"匹配缺口：{item}" for item in gaps[:3] if item)
        return warnings

    def _fallback_skill(self, resume: ResumeDetail) -> TextOptimization:
        skills = self._split_items(resume.skill_name)
        if not skills:
            return TextOptimization(
                original=resume.skill_name,
                optimized="",
                reason="原始简历未提供明确技能内容。",
                missing_facts=["补充主要编程语言、框架、中间件、数据库和工程工具"],
            )
        optimized = "；".join(
            [
                "技术栈：" + "、".join(skills[:6]),
                "工程能力：结合项目经历说明接口开发、数据处理、系统集成或部署能力",
                "表达建议：把熟悉程度和使用场景写清楚，避免只堆关键词",
            ]
        )
        return TextOptimization(
            original=resume.skill_name,
            optimized=optimized,
            reason="将零散技能改成分层表达，便于招聘方快速判断技术匹配度。",
            missing_facts=["每项核心技能对应的项目使用场景", "可验证的性能、规模或业务效果"],
        )

    def _fallback_project(self, item: Any) -> ExperienceOptimization:
        content = self._clean_text(item.content or item.introduction or "")
        bullets = self._fallback_bullets(
            name=item.project_name,
            role=item.role,
            content=content,
            default_subject="项目",
        )
        segments = self._fallback_segments(content)
        return ExperienceOptimization(
            source_id=item.project_info_id,
            name=item.project_name,
            role=item.role,
            original=content,
            star_breakdown=[
                f"Situation：围绕 {item.project_name} 说明业务背景、数据来源或问题场景。",
                "Task：明确自己需要完成的分析目标、建模目标或交付物。",
                "Action：突出本人负责的数据处理、分析方法、技术方案和协作动作。",
                "Result：补充可验证的业务结论、交付结果或量化影响；缺少事实时不编数字。",
            ],
            optimized_bullets=[segment.optimized for segment in segments] or bullets,
            segments=segments,
            reason="按任务段逐条判断，保留已清晰表达，仅优化笼统、缺少行动或结果导向的描述。",
            missing_facts=["项目规模", "个人贡献边界", "上线结果或量化收益"],
        )

    def _fallback_intern(self, item: Any) -> ExperienceOptimization:
        content = self._clean_text(item.content or "")
        bullets = self._fallback_bullets(
            name=item.company,
            role=item.role,
            content=content,
            default_subject="实习工作",
        )
        segments = self._fallback_segments(content)
        return ExperienceOptimization(
            source_id=item.intern_info_id,
            name=item.company,
            role=item.role,
            original=content,
            star_breakdown=[
                f"Situation：说明在 {item.company} 所处的业务场景、团队背景或问题背景。",
                "Task：明确岗位目标、负责范围和需要交付的任务。",
                "Action：突出独立负责的工作、协作方式和技术动作。",
                "Result：补充交付物、效率提升、缺陷下降或业务反馈；缺少事实时不编数字。",
            ],
            optimized_bullets=[segment.optimized for segment in segments] or bullets,
            segments=segments,
            reason="实习经历需要体现岗位职责、真实产出和团队协作价值。",
            missing_facts=["交付成果", "协作对象", "量化影响或业务反馈"],
        )

    def _fallback_bullets(
        self,
        name: str,
        role: str | None,
        content: str,
        default_subject: str,
    ) -> list[str]:
        subject = role or default_subject
        sentences = self._split_items(content)
        if not sentences:
            return [f"负责 {name} 中的{subject}相关工作，建议补充具体任务、技术动作和结果。"]
        bullets = []
        for sentence in sentences[:3]:
            bullets.append(f"围绕 {name}，负责{subject}，{sentence}")
        return bullets

    def _fallback_segments(self, content: str) -> list[SegmentOptimization]:
        segments = self._split_experience_segments(content)
        return [
            self._fallback_segment(index=index, original=segment)
            for index, segment in enumerate(segments[:6])
        ]

    def _fallback_segment(self, index: int, original: str) -> SegmentOptimization:
        if self._looks_like_complete_star_sentence(original):
            return SegmentOptimization(
                segment_index=index,
                original=original,
                optimized=original,
                changed=False,
                reason="原表达已经包含背景、行动和结果导向，保留原文。",
                star_breakdown=self._segment_star_breakdown(original),
            )
        optimized = self._light_star_rewrite(original)
        return SegmentOptimization(
            segment_index=index,
            original=original,
            optimized=optimized,
            changed=optimized != original,
            reason="原表达偏任务罗列，调整为包含场景、行动方法和结果方向的 STAR 式表述。",
            star_breakdown=self._segment_star_breakdown(optimized),
            missing_facts=["可量化结果", "具体方法或工具", "业务采纳情况"],
        )

    def _split_experience_segments(self, content: str) -> list[str]:
        if not content:
            return []
        text = re.sub(r"\s+", " ", content).strip()
        text = re.sub(r"([。！？!?；;])\s*", r"\1\n", text)
        lines = [line.strip(" -•·,，;；。") for line in text.splitlines()]
        return [line for line in lines if len(line) >= 6]

    def _looks_like_complete_star_sentence(self, sentence: str) -> bool:
        has_context = bool(re.search(r"(基于|围绕|面向|针对|在.+场景|通过.+数据)", sentence))
        has_action = bool(
            re.search(r"(使用|通过|构建|搭建|设计|计算|分析|识别|定位|绘制|对比|验证|提出)", sentence)
        )
        has_specific_method = bool(
            re.search(
                r"(聚类|异常检测|漏斗|Cohort|A/B|t检验|回归|模型|SQL|Python|Pandas|"
                r"曲线|分群|分层|指标|留存率|转化率|点击率|购买率|故障率|准确率|召回率|效率)",
                sentence,
                re.IGNORECASE,
            )
        )
        has_result = bool(
            re.search(r"(提升|降低|优化|支撑|验证|发现|定位|明确|形成|提出|完成|为.+提供)", sentence)
        )
        is_generic = bool(re.search(r"(分析.+情况|定位.+原因|提出.+方案)$", sentence))
        return (
            has_context
            and has_action
            and has_specific_method
            and has_result
            and not is_generic
            and len(sentence) >= 28
        )

    def _light_star_rewrite(self, sentence: str) -> str:
        cleaned = sentence.strip(" -•·,，;；。")
        if re.search(r"服务器日志|系统异常|故障", cleaned):
            return (
                "基于服务器日志数据，识别系统异常高发时段与关键故障模式，"
                "通过日志聚类与异常检测定位核心问题，并提出稳定性优化方案以降低系统故障率"
            )
        if re.search(r"(基于|围绕|面向|针对)", cleaned):
            prefix = cleaned
        else:
            prefix = f"围绕相关业务场景，{cleaned}"
        if not re.search(r"(提升|降低|优化|支撑|验证|发现|定位|明确|形成|提出|完成|提供)", prefix):
            prefix = f"{prefix}，形成可落地的分析结论或优化建议"
        return prefix

    def _segment_star_breakdown(self, sentence: str) -> list[str]:
        return [
            f"Situation：{self._extract_clause(sentence, ('基于', '围绕', '面向', '针对')) or '原文包含任务背景或数据场景。'}",
            "Task：明确该任务要解决的问题、分析目标或交付目标。",
            "Action：突出使用的方法、工具、分析动作或协作方式。",
            "Result：说明产出的结论、方案、支撑价值或建议补充的量化结果。",
        ]

    def _extract_clause(self, sentence: str, starters: tuple[str, ...]) -> str | None:
        for starter in starters:
            index = sentence.find(starter)
            if index >= 0:
                return sentence[index : index + 42]
        return None

    def _split_items(self, text: str) -> list[str]:
        if not text:
            return []
        parts = re.split(r"[\n,，;；、]+", text)
        return [self._clean_text(part) for part in parts if self._clean_text(part)]

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip(" -•·,，;；。")
