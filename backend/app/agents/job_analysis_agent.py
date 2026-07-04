import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.agents.base import BaseAgent
from app.schemas.job import (
    CompensationMarket,
    CustomizationPlan,
    InterviewPlan,
    InterviewStoryPrompt,
    JobAnalysisResult,
    JobAuthenticityCheck,
    JobScoring,
    JobSummary,
    LevelStrategy,
    RequirementMapping,
    ResumeMatchAnalysis,
    ScoreDimension,
)
from app.schemas.resume import ResumeDetail


class JobAnalysisAgent(BaseAgent):
    system_prompt = (
        "你是岗位分析 Agent，负责在简历优化前判断岗位是否值得投、如何投、后续简历和面试故事应聚焦什么。"
        "你必须只基于输入的简历 JSON、岗位抓取文本和抓取元数据推理；没有证据的薪资、口碑、趋势要标为 unknowns，"
        "不得编造公司事实、岗位要求、薪酬数字或候选人经历。"
        "如果输入显示岗位页面 404、已关闭、已停止招聘、跳到通用招聘页、缺少职位标题/JD/申请入口，"
        "必须停止正常匹配分析，将 suitable=false，authenticityCheck 写明 stopReason。"
        "但当抓取来源 source=manual 时，岗位描述来自用户手动粘贴；此时不要因为缺少网页申请入口而停止分析，"
        "只需在真实性检查中说明原始页面未验证。"
        "输出必须是严格 JSON，不要 markdown，不要额外解释。"
    )

    def analyze(self, resume: ResumeDetail, job_content: str) -> JobAnalysisResult:
        if self.should_use_mock():
            if not self.allow_fallback:
                self.raise_real_llm_required()
            return self._mock_analyze()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                (
                    "human",
                    "\n".join(
                        [
                            "请按照下面 JSON Schema 输出岗位分析结果，只返回一个 JSON 对象。",
                            "分析流程：",
                            "1. 先做岗位真实性检查：读取抓取来源、finalUrl、HTTP 状态、active/redFlags/signals。",
                            "2. 如果岗位不可用或疑似幽灵岗位，停止 A-F 的深入分析，只保留 G 和停止原因。",
                            "3. 如果 source=manual 且 rawContent 包含岗位职责/任职要求，则继续分析 A-F，"
                            "G 中标注“用户手动粘贴，原始网页真实性待验证”。",
                            "4. 岗位可用时，识别岗位原型/类型，并输出 A-G 七块内容。",
                            "5. A 职位摘要：岗位类型、领域、职能、资历、远程/混合/现场、TL;DR。",
                            "6. B 简历匹配：逐条把 JD 要求映射到简历证据；缺口写 gap，补救写 remedy。",
                            "7. C 职级与申请策略：判断职级，说明如何卖高级但不造假。",
                            "8. D 薪资与市场需求：只引用输入中的薪资/搜索片段/页面证据；缺失则写 unknowns。",
                            "9. E 定制计划：给出简历和 LinkedIn 修改建议，列 keywordFocus/rewriteFocus。",
                            "10. F 面试计划：把 JD 要求映射到 STAR+R 故事，Result 不允许编数字。",
                            "11. G 岗位真实性检查：判断真实开放、疑似幽灵、风险或未知，并列信号和红旗。",
                            "12. scoring 使用 0-100 分和权重：简历匹配 0.35、岗位目标一致 0.2、薪酬/成长 0.15、"
                            "文化/工作方式 0.1、真实性/风险 0.2。globalScore 是加权结果。",
                            "13. matchScore 优先等于“简历匹配”维度分；suitable 根据 globalScore、真实性和关键 gap 综合判断。",
                            "14. optimizationFocus/starStoryFocus/resumeRewriteFocus 必须能直接指导后续优化 agent。",
                            "JSON Schema:\n{schema}",
                            "简历 JSON:\n{resume_json}",
                            "岗位抓取内容与元数据:\n{job_content}",
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
                    "schema": json.dumps(
                        JobAnalysisResult.model_json_schema(by_alias=True),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "resume_json": resume.model_dump_json(by_alias=True),
                    "job_content": job_content[:24000],
                },
            )
            return self._finalize_result(
                JobAnalysisResult.model_validate(self._load_json_object(response.content))
            )
        except Exception:
            if not self.allow_fallback:
                raise
            return self._mock_analyze(
                "LLM analysis failed after retries. Returned fallback scaffold result."
            )

    def _mock_analyze(self, reason: str = "Mock mode: replace with real LangChain analysis.") -> JobAnalysisResult:
        mappings = [
            RequirementMapping(
                requirement="从岗位 JD 中提取核心职责、硬技能和加分项。",
                importance="high",
                resume_evidence=["Mock 模式未读取真实 LLM 结论。"],
                gap="需要接入真实 LLM 后逐条映射简历证据。",
                remedy="补充岗位关键要求与简历项目/实习经历之间的一一对应关系。",
            )
        ]
        scoring = JobScoring(
            dimensions=[
                ScoreDimension(
                    name="简历匹配",
                    score=60.0,
                    weight=0.35,
                    rationale="Mock 模式默认中等匹配，需真实分析替换。",
                ),
                ScoreDimension(
                    name="岗位目标一致",
                    score=60.0,
                    weight=0.2,
                    rationale="缺少真实岗位原型判断。",
                ),
                ScoreDimension(
                    name="薪酬/成长",
                    score=50.0,
                    weight=0.15,
                    rationale="未查询到薪资与市场证据。",
                ),
                ScoreDimension(
                    name="文化/工作方式",
                    score=60.0,
                    weight=0.1,
                    rationale="未查询到工作方式证据。",
                ),
                ScoreDimension(
                    name="真实性/风险",
                    score=70.0,
                    weight=0.2,
                    rationale="Mock 模式无法验证页面真实性。",
                ),
            ],
            global_score=61.5,
            recommendation="谨慎申请：请开启真实 LLM 与岗位抓取后再决策。",
            score_band="3.0/5 mock",
        )
        return JobAnalysisResult(
            match_score=60.0,
            suitable=True,
            confidence_source=[reason],
            analysis="Mock 岗位分析结果。生产环境请接入真实 LLM 与网页抓取证据。",
            job_archetype="unknown",
            job_summary=JobSummary(
                job_type="未知",
                domain="未知",
                function="未知",
                seniority="未知",
                work_mode="未知",
                tldr="Mock 模式无法给出真实岗位摘要。",
            ),
            resume_match=ResumeMatchAnalysis(
                key_matches=[],
                mappings=mappings,
                gaps=["真实匹配缺口需要基于 JD 与简历重新分析。"],
                remedies=["开启真实 LLM 后生成逐条补救策略。"],
            ),
            level_strategy=LevelStrategy(
                inferred_level="未知",
                positioning="基于真实 JD 判断职级后，再选择初级/中级/高级表达策略。",
            ),
            compensation_market=CompensationMarket(
                salary_range="未知",
                market_demand="未知",
                compensation_reputation="未知",
                unknowns=["需要通过岗位页、招聘平台或薪酬网站查验薪资与需求趋势。"],
            ),
            customization_plan=CustomizationPlan(
                resume_changes=["围绕岗位高权重要求重排技能、项目和实习经历。"],
                linkedin_changes=["同步更新 headline、about 和 featured 项目关键词。"],
                keyword_focus=["岗位关键词待真实分析后填充。"],
                rewrite_focus=["STAR+R 表达", "证据优先", "不编造量化结果"],
            ),
            interview_plan=InterviewPlan(
                star_story_prompts=[
                    InterviewStoryPrompt(
                        requirement="岗位核心要求",
                        story_angle="选择最能证明匹配度的项目或实习故事。",
                        resume_evidence="Mock 模式暂无真实证据。",
                        star_r_outline=[
                            "Situation：岗位相关业务/技术背景",
                            "Task：本人负责的目标",
                            "Action：方法、工具、协作动作",
                            "Result：可验证产出；缺数字则说明待补充",
                        ],
                        missing_facts=["真实成果指标", "项目规模", "个人贡献边界"],
                    )
                ],
                likely_questions=["请介绍一个最匹配该岗位要求的项目。"],
                prep_tasks=["补充可验证的项目结果和技术细节。"],
            ),
            authenticity_check=JobAuthenticityCheck(
                verdict="unknown",
                confidence="low",
                active_signals=[],
                red_flags=["Mock 模式未做真实网页验证。"],
            ),
            scoring=scoring,
            optimization_focus=["优先补齐岗位高权重要求与简历证据的映射。"],
            star_story_focus=["围绕最匹配岗位要求的项目准备 STAR+R 故事。"],
            resume_rewrite_focus=["保留事实边界，强化岗位关键词和结果表达。"],
        )

    def _finalize_result(self, result: JobAnalysisResult) -> JobAnalysisResult:
        if result.match_score is None:
            result.match_score = self._score_dimension(result, "简历匹配")
        if result.scoring.global_score is None:
            result.scoring.global_score = self._weighted_score(result.scoring.dimensions)
        if result.suitable is None:
            authenticity = result.authenticity_check.verdict.lower()
            result.suitable = bool(
                (result.scoring.global_score or result.match_score or 0) >= 65
                and "ghost" not in authenticity
                and "closed" not in authenticity
                and "expired" not in authenticity
            )
        if not result.analysis:
            result.analysis = self._format_short_analysis(result)
        if not result.optimization_focus:
            result.optimization_focus = result.customization_plan.keyword_focus[:5]
        if not result.star_story_focus:
            result.star_story_focus = [
                item.story_angle
                for item in result.interview_plan.star_story_prompts
                if item.story_angle
            ][:5]
        if not result.resume_rewrite_focus:
            result.resume_rewrite_focus = result.customization_plan.rewrite_focus[:5]
        return result

    def _score_dimension(self, result: JobAnalysisResult, keyword: str) -> float | None:
        for dimension in result.scoring.dimensions:
            if keyword in dimension.name and dimension.score is not None:
                return dimension.score
        return result.scoring.global_score

    def _weighted_score(self, dimensions: list[ScoreDimension]) -> float | None:
        total_weight = sum(d.weight or 0 for d in dimensions if d.score is not None)
        if total_weight <= 0:
            scores = [d.score for d in dimensions if d.score is not None]
            return sum(scores) / len(scores) if scores else None
        return sum((d.score or 0) * (d.weight or 0) for d in dimensions) / total_weight

    def _format_short_analysis(self, result: JobAnalysisResult) -> str:
        summary = result.job_summary.tldr or "岗位摘要不足。"
        recommendation = result.scoring.recommendation or "暂无明确建议。"
        return f"{summary}\n申请建议：{recommendation}"

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
            raise ValueError("Job analysis agent must return a JSON object.")
        return payload
