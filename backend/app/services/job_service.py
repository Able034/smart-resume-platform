import json
import re
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.job_analysis_agent import JobAnalysisAgent
from app.core.exceptions import AppException, BAD_REQUEST, NOT_FOUND
from app.crawlers.job_crawler import JobCrawler, JobCrawlResult
from app.models import Job, Resume
from app.schemas.job import (
    JobAnalysisResult,
    JobAnalyzeResponse,
    JobAuthenticityCheck,
    JobListItem,
)
from app.services.resume_service import ResumeService


class JobService:
    def __init__(self, db: Session):
        self.db = db

    def analyze(
        self,
        resume_id: int,
        user_id: int,
        job_url: str | None = None,
        job_description: str | None = None,
    ) -> JobAnalyzeResponse:
        self._assert_resume_owner(resume_id, user_id)
        job_url = job_url.strip() if job_url else None
        job_description = job_description.strip() if job_description else None
        if not job_url and not job_description:
            raise AppException(BAD_REQUEST, "Job URL or job description is required.", 400)

        crawl = (
            self._manual_crawl(job_description, job_url)
            if job_description
            else JobCrawler().fetch(job_url or "")
        )
        resume = ResumeService(self.db).get_detail_for_user(resume_id, user_id)
        analysis = (
            JobAnalysisAgent().analyze(resume, self._format_crawl_for_agent(crawl))
            if crawl.ok
            else None
        )
        content_payload = {
            "rawContent": crawl.content,
            "crawl": self._crawl_metadata(crawl),
            "analysis": analysis.model_dump(by_alias=True) if analysis else None,
        }
        job = Job(
            resume_id=resume_id,
            job_url=job_url or "manual://job-description",
            job_name=crawl.job_name,
            company=crawl.company,
            content=json.dumps(content_payload, ensure_ascii=False),
            status=self._crawl_status(crawl),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return self._to_analyze_response(job, analysis or self._failed_job_analysis(crawl))

    def list_by_resume(self, resume_id: int, user_id: int) -> list[JobListItem]:
        self._assert_resume_owner(resume_id, user_id)
        rows = self.db.scalars(
            select(Job).where(Job.resume_id == resume_id).order_by(Job.created_at.desc())
        ).all()
        return [
            JobListItem(
                job_id=row.job_id,
                job_name=row.job_name,
                company=row.company,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def get_detail(self, job_id: int, user_id: int) -> JobAnalyzeResponse:
        job = self.db.get(Job, job_id)
        if not job:
            raise AppException(NOT_FOUND, "Job not found", 404)
        self._assert_resume_owner(job.resume_id, user_id)
        return self._to_analyze_response(job, self._analysis_from_job_content(job.content))

    def _assert_resume_owner(self, resume_id: int, user_id: int) -> None:
        exists = self.db.scalar(
            select(Resume.resume_id).where(
                Resume.resume_id == resume_id,
                Resume.user_id == user_id,
                Resume.deleted_at.is_(None),
            )
        )
        if not exists:
            raise AppException(NOT_FOUND, "Resume not found", 404)

    def _format_crawl_for_agent(self, crawl: object) -> str:
        payload = asdict(crawl)
        payload["rawContent"] = payload.pop("content", "")
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _to_analyze_response(
        self,
        job: Job,
        analysis: JobAnalysisResult,
    ) -> JobAnalyzeResponse:
        return JobAnalyzeResponse(
            job_id=job.job_id,
            resume_id=job.resume_id,
            job_url=job.job_url,
            job_name=job.job_name,
            company=job.company,
            content=job.content,
            status=job.status,
            created_at=job.created_at,
            match_score=analysis.match_score,
            suitable=analysis.suitable,
            confidence_source=analysis.confidence_source,
            analysis=analysis.analysis,
            job_archetype=analysis.job_archetype,
            job_summary=analysis.job_summary,
            resume_match=analysis.resume_match,
            level_strategy=analysis.level_strategy,
            compensation_market=analysis.compensation_market,
            customization_plan=analysis.customization_plan,
            interview_plan=analysis.interview_plan,
            authenticity_check=analysis.authenticity_check,
            scoring=analysis.scoring,
            optimization_focus=analysis.optimization_focus,
            star_story_focus=analysis.star_story_focus,
            resume_rewrite_focus=analysis.resume_rewrite_focus,
        )

    def _analysis_from_job_content(self, content: str) -> JobAnalysisResult:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return JobAnalysisResult(analysis="岗位内容不是有效 JSON，无法读取结构化分析。")
        if not isinstance(payload, dict):
            return JobAnalysisResult(analysis="岗位内容格式异常，无法读取结构化分析。")
        analysis = payload.get("analysis")
        if isinstance(analysis, dict):
            return JobAnalysisResult.model_validate(analysis)
        return JobAnalysisResult(analysis="暂无结构化岗位分析结果。")

    def _manual_crawl(
        self,
        job_description: str | None,
        job_url: str | None,
    ) -> JobCrawlResult:
        content = self._normalize_manual_job_description(job_description or "")
        return JobCrawlResult(
            job_name=self._infer_manual_job_name(content),
            company=None,
            content=content,
            ok=True,
            source="manual",
            final_url=job_url or "manual://job-description",
            active=True,
            signals=["用户手动粘贴岗位描述，跳过网页抓取。"],
            red_flags=[] if job_url else ["未提供岗位 URL，无法验证原始页面真实性。"],
        )

    def _infer_manual_job_name(self, content: str) -> str | None:
        for raw_line in content.splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip(" #*-：:")
            if not line:
                continue
            line = re.sub(
                r"^(岗位名称|职位名称|招聘岗位|职位|岗位|job title|title)\s*[:：]\s*",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip()
            if 2 <= len(line) <= 80:
                return line[:150]
        return "手动粘贴岗位"

    def _normalize_manual_job_description(self, content: str) -> str:
        text = re.sub(r"\r\n?", "\n", content).strip()
        replacements = {
            "岗位职麦": "岗位职责",
            "职麦": "职责",
            "负麦": "负责",
            "交档": "文档",
            "学握": "掌握",
            "MySOL": "MySQL",
            "MysOL": "MySQL",
            "MySQl": "MySQL",
            "mySOL": "MySQL",
            "S0L": "SQL",
            "s0l": "SQL",
            "1.扎实": "1. 扎实",
            "2.熟悉": "2. 熟悉",
            "3.熟悉": "3. 熟悉",
            "4.数据库": "4. 数据库",
            "5.Web": "5. Web",
            "HTMLCSS": "HTML、CSS",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = re.sub(r"(?i)springboot", "SpringBoot", text)
        text = re.sub(r"(?i)springmvc", "SpringMVC", text)
        text = re.sub(r"(?i)mybatis", "MyBatis", text)
        text = re.sub(r"(?i)redis", "Redis", text)
        text = re.sub(r"(?i)mysql", "MySQL", text)
        text = re.sub(r"(?i)javascript", "JavaScript", text)
        text = re.sub(r"(?i)vue", "Vue", text)
        text = re.sub(r"(?i)react", "React", text)
        return text

    def _crawl_metadata(self, crawl: object) -> dict:
        payload = asdict(crawl)
        content = payload.pop("content", "")
        payload["contentSnippet"] = content[:1000]
        return payload

    def _crawl_status(self, crawl: object) -> str:
        if getattr(crawl, "ok", False):
            return "PARSED"
        if getattr(crawl, "active", None) is False:
            return "EXPIRED"
        if self._is_blocked_by_security(crawl):
            return "BLOCKED"
        return "FAILED"

    def _failed_analysis_text(self, crawl: object) -> str:
        reason = getattr(crawl, "failure_reason", None) or "Job crawl failed."
        if getattr(crawl, "active", None) is False:
            return f"岗位页面不可用，已停止分析：{reason}"
        if self._is_blocked_by_security(crawl):
            return f"岗位页面被招聘平台安全验证拦截，已停止分析：{reason}"
        return f"岗位抓取失败，未进行匹配分析：{reason}"

    def _failed_job_analysis(self, crawl: object) -> JobAnalysisResult:
        red_flags = list(getattr(crawl, "red_flags", []) or [])
        reason = self._failed_analysis_text(crawl)
        if getattr(crawl, "active", None) is False:
            verdict = "closed_or_expired"
        elif self._is_blocked_by_security(crawl):
            verdict = "blocked_by_security_verification"
        else:
            verdict = "unknown_or_unreachable"
        return JobAnalysisResult(
            match_score=None,
            suitable=False,
            confidence_source=[getattr(crawl, "source", "crawler")],
            analysis=reason,
            authenticity_check=JobAuthenticityCheck(
                verdict=verdict,
                confidence="high" if red_flags else "medium",
                active_signals=list(getattr(crawl, "signals", []) or []),
                red_flags=red_flags,
                stop_reason=reason,
            ),
        )

    def _is_blocked_by_security(self, crawl: object) -> bool:
        text = " ".join(
            [
                str(getattr(crawl, "failure_reason", "") or ""),
                str(getattr(crawl, "final_url", "") or ""),
                " ".join(getattr(crawl, "red_flags", []) or []),
            ]
        ).lower()
        return any(
            keyword in text
            for keyword in (
                "security verification",
                "security.html",
                "安全验证",
                "反爬",
                "captcha",
            )
        )
