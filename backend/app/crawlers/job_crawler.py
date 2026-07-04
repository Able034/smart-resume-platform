from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx
from bs4 import BeautifulSoup


os.environ.pop("SSLKEYLOGFILE", None)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 SmartResumeBot/1.0"
)


@dataclass
class JobCrawlResult:
    job_name: str | None
    company: str | None
    content: str
    ok: bool = True
    source: str = "webfetch"
    final_url: str | None = None
    status_code: int | None = None
    active: bool | None = None
    signals: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    failure_reason: str | None = None


@dataclass
class _JobPageValidation:
    sufficient: bool
    definitive_inactive: bool
    reason: str | None
    signals: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)


class JobCrawler:
    closed_keywords = (
        "职位已关闭",
        "岗位已关闭",
        "职位已下线",
        "岗位已下线",
        "停止招聘",
        "暂停招聘",
        "已招满",
        "该职位不存在",
        "职位不存在",
        "job expired",
        "job is expired",
        "job has expired",
        "job closed",
        "position closed",
        "no longer accepting applications",
        "no longer available",
        "not accepting applications",
        "this job is no longer available",
    )
    jd_keywords = (
        "岗位职责",
        "职位描述",
        "工作职责",
        "任职要求",
        "岗位要求",
        "职位要求",
        "加分项",
        "responsibilities",
        "qualifications",
        "requirements",
        "what you will do",
        "what you'll do",
        "about the role",
        "minimum qualifications",
    )
    apply_keywords = (
        "立即申请",
        "申请职位",
        "投递简历",
        "我要投递",
        "apply now",
        "apply for this job",
        "submit application",
        "easy apply",
    )
    security_challenge_keywords = (
        "请稍候",
        "安全验证",
        "身份验证",
        "访问验证",
        "验证一下",
        "captcha",
        "security check",
        "verify you are human",
        "checking your browser",
    )
    security_challenge_paths = (
        "/security.html",
        "/passport/",
        "/captcha",
        "/verify",
        "/waf",
    )
    generic_paths = (
        "",
        "/",
        "/jobs",
        "/job",
        "/careers",
        "/career",
        "/positions",
        "/openings",
        "/join-us",
        "/recruitment",
    )

    def fetch(self, job_url: str) -> JobCrawlResult:
        failures: list[str] = []

        for fetcher in (self._fetch_with_playwright, self._fetch_with_webfetch):
            candidate = fetcher(job_url)
            if not candidate.ok:
                failures.append(self._failure_message(candidate))
                continue

            validation = self._validate_job_page(candidate, job_url)
            candidate.signals = self._unique([*candidate.signals, *validation.signals])
            candidate.red_flags = self._unique([*candidate.red_flags, *validation.red_flags])

            if validation.definitive_inactive:
                candidate.ok = False
                candidate.active = False
                candidate.failure_reason = validation.reason
                return candidate

            if validation.sufficient:
                candidate.ok = True
                candidate.active = True
                return candidate

            candidate.ok = False
            candidate.active = None
            candidate.failure_reason = validation.reason or "Job page content was insufficient."
            failures.append(self._failure_message(candidate))

        search_candidate = self._fetch_with_websearch(job_url)
        if search_candidate.ok:
            validation = self._validate_job_page(search_candidate, job_url)
            search_candidate.signals = self._unique(
                [*search_candidate.signals, *validation.signals]
            )
            search_candidate.red_flags = self._unique(
                [*search_candidate.red_flags, *validation.red_flags]
            )
            if validation.sufficient and not validation.definitive_inactive:
                search_candidate.active = True
                return search_candidate
            search_candidate.ok = False
            search_candidate.active = False if validation.definitive_inactive else None
            search_candidate.failure_reason = (
                validation.reason or "WebSearch fallback did not confirm an active job."
            )
            failures.append(self._failure_message(search_candidate))
        else:
            failures.append(self._failure_message(search_candidate))

        return JobCrawlResult(
            job_name=None,
            company=None,
            content="Unable to confirm an active job posting.\n" + "\n".join(failures),
            ok=False,
            source="none",
            final_url=job_url,
            active=None,
            red_flags=self._unique(failures),
            failure_reason="Playwright, WebFetch, and WebSearch all failed to confirm an active job.",
        )

    def _fetch_with_playwright(self, job_url: str) -> JobCrawlResult:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            return JobCrawlResult(
                job_name=None,
                company=None,
                content="Playwright is unavailable.",
                ok=False,
                source="playwright",
                final_url=job_url,
                failure_reason=str(exc),
            )

        timeout_ms = int(os.getenv("JOB_CRAWLER_PLAYWRIGHT_TIMEOUT_MS", "15000"))
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(user_agent=USER_AGENT)
                response = page.goto(job_url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                html = page.content()
                title = page.title()
                final_url = page.url
                status_code = response.status if response else None
                browser.close()
        except Exception as exc:
            return JobCrawlResult(
                job_name=None,
                company=None,
                content=f"Playwright failed to read job url: {job_url}\nReason: {exc}",
                ok=False,
                source="playwright",
                final_url=job_url,
                failure_reason=str(exc),
            )

        result = self._parse_html(
            html=html,
            final_url=final_url,
            status_code=status_code,
            source="playwright",
        )
        if not result.job_name and title:
            result.job_name = title[:150]
        return result

    def _fetch_with_webfetch(self, job_url: str) -> JobCrawlResult:
        try:
            response = httpx.get(
                job_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
                follow_redirects=True,
            )
        except Exception as exc:
            return JobCrawlResult(
                job_name=None,
                company=None,
                content=f"WebFetch failed to crawl job url: {job_url}\nReason: {exc}",
                ok=False,
                source="webfetch",
                final_url=job_url,
                failure_reason=str(exc),
            )

        if response.status_code >= 400:
            return JobCrawlResult(
                job_name=None,
                company=None,
                content=response.text[:2000],
                ok=True,
                source="webfetch",
                final_url=str(response.url),
                status_code=response.status_code,
            )

        return self._parse_html(
            html=response.text,
            final_url=str(response.url),
            status_code=response.status_code,
            source="webfetch",
        )

    def _fetch_with_websearch(self, job_url: str) -> JobCrawlResult:
        query = f'"{job_url}" job posting'
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            response = httpx.get(
                search_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
                follow_redirects=True,
            )
            response.raise_for_status()
        except Exception as exc:
            return JobCrawlResult(
                job_name=None,
                company=None,
                content=f"WebSearch failed for job url: {job_url}\nReason: {exc}",
                ok=False,
                source="websearch",
                final_url=search_url,
                failure_reason=str(exc),
            )

        soup = BeautifulSoup(response.text, "html.parser")
        snippets: list[str] = []
        for result in soup.select(".result")[:5]:
            title = self._clean_text(result.select_one(".result__title"))
            snippet = self._clean_text(result.select_one(".result__snippet"))
            url = self._clean_text(result.select_one(".result__url"))
            line = " | ".join(part for part in (title, snippet, url) if part)
            if line:
                snippets.append(line)

        content = "WebSearch fallback snippets:\n" + "\n".join(snippets)
        return JobCrawlResult(
            job_name=snippets[0][:150] if snippets else None,
            company=None,
            content=content[:20000],
            ok=bool(snippets),
            source="websearch",
            final_url=search_url,
            status_code=response.status_code,
            failure_reason=None if snippets else "WebSearch returned no usable snippets.",
        )

    def _parse_html(
        self,
        html: str,
        final_url: str,
        status_code: int | None,
        source: str,
    ) -> JobCrawlResult:
        soup = BeautifulSoup(html, "html.parser")
        structured = self._extract_structured_job(soup)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        page_title = soup.title.get_text(" ", strip=True) if soup.title else None
        h1 = soup.find("h1")
        job_name = structured.get("title") or self._clean_text(h1) or page_title
        company = structured.get("company") or self._extract_company(soup)
        page_text = soup.get_text("\n", strip=True)
        structured_text = "\n".join(
            str(value)
            for value in (
                structured.get("title"),
                structured.get("company"),
                structured.get("description"),
                structured.get("employmentType"),
                structured.get("jobLocation"),
                structured.get("baseSalary"),
            )
            if value
        )
        content = "\n".join(part for part in (structured_text, page_text) if part)
        return JobCrawlResult(
            job_name=job_name[:150] if job_name else None,
            company=company[:150] if company else None,
            content=content[:20000],
            ok=True,
            source=source,
            final_url=final_url,
            status_code=status_code,
        )

    def _extract_structured_job(self, soup: BeautifulSoup) -> dict[str, str]:
        for script in soup.find_all("script", type=lambda value: value and "ld+json" in value):
            raw = script.string or script.get_text()
            if not raw.strip():
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for node in self._iter_json_nodes(payload):
                node_type = node.get("@type")
                if isinstance(node_type, list):
                    is_job = any(str(item).lower() == "jobposting" for item in node_type)
                else:
                    is_job = str(node_type).lower() == "jobposting"
                if not is_job:
                    continue
                organization = node.get("hiringOrganization") or {}
                salary = node.get("baseSalary") or ""
                location = node.get("jobLocation") or ""
                description = node.get("description") or ""
                return {
                    "title": str(node.get("title") or ""),
                    "company": str(organization.get("name") if isinstance(organization, dict) else ""),
                    "description": BeautifulSoup(str(description), "html.parser").get_text(
                        "\n", strip=True
                    ),
                    "employmentType": str(node.get("employmentType") or ""),
                    "jobLocation": self._stringify_json_value(location),
                    "baseSalary": self._stringify_json_value(salary),
                }
        return {}

    def _iter_json_nodes(self, value: Any):
        if isinstance(value, dict):
            yield value
            graph = value.get("@graph")
            if graph is not None:
                yield from self._iter_json_nodes(graph)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_json_nodes(item)

    def _extract_company(self, soup: BeautifulSoup) -> str | None:
        meta_names = (
            "company",
            "og:site_name",
            "twitter:site",
            "application-name",
        )
        for name in meta_names:
            tag = soup.find("meta", attrs={"property": name}) or soup.find(
                "meta", attrs={"name": name}
            )
            content = tag.get("content") if tag else None
            if content:
                return str(content).strip()
        company_patterns = re.compile(r"(company|employer|org|brand)", re.IGNORECASE)
        tag = soup.find(attrs={"class": company_patterns}) or soup.find(
            attrs={"data-testid": company_patterns}
        )
        return self._clean_text(tag) or None

    def _validate_job_page(
        self,
        result: JobCrawlResult,
        original_url: str,
    ) -> _JobPageValidation:
        text = self._normalize_text(result.content)
        title = self._normalize_text(result.job_name or "")
        combined = f"{title}\n{text}"
        signals: list[str] = []
        red_flags: list[str] = []

        if result.status_code in {404, 410}:
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=True,
                reason=f"Job page returned HTTP {result.status_code}.",
                red_flags=[f"HTTP {result.status_code}"],
            )

        if result.status_code and result.status_code >= 400:
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=False,
                reason=f"Job page returned HTTP {result.status_code}.",
                red_flags=[f"HTTP {result.status_code}"],
            )

        if self._is_security_challenge(result.final_url, combined):
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=False,
                reason=(
                    "Job platform returned a security verification page instead "
                    "of the concrete job detail."
                ),
                red_flags=["招聘平台返回安全验证/反爬页面，未拿到岗位详情。"],
            )

        if self._contains_any(combined, self.closed_keywords):
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=True,
                reason="Page contains closed/expired job signals.",
                red_flags=["页面包含已关闭、已下线或停止招聘信号。"],
            )

        has_title = self._looks_like_job_title(title)
        jd_hit_count = self._count_keyword_hits(text, self.jd_keywords)
        has_jd = jd_hit_count >= 2 or (len(text) >= 250 and jd_hit_count >= 1)
        has_apply = self._contains_any(text, self.apply_keywords)
        generic_redirect = self._is_generic_redirect(original_url, result.final_url)

        if has_title:
            signals.append("检测到职位标题。")
        else:
            red_flags.append("未检测到明确职位标题。")
        if has_jd:
            signals.append("检测到职位描述/任职要求。")
        else:
            red_flags.append("未检测到完整 JD。")
        if has_apply:
            signals.append("检测到申请入口或投递动作。")
        else:
            red_flags.append("未检测到申请入口。")

        if generic_redirect and not (has_title and has_jd):
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=True,
                reason="URL redirected to a generic careers/jobs page instead of a concrete job.",
                signals=signals,
                red_flags=[*red_flags, "岗位 URL 跳转到通用招聘页。"],
            )

        if len(text) < 300 and not (has_title and has_jd and has_apply):
            return _JobPageValidation(
                sufficient=False,
                definitive_inactive=False,
                reason="Extracted page text is too short to analyze.",
                signals=signals,
                red_flags=red_flags,
            )

        sufficient = has_jd and (has_title or has_apply or len(text) >= 1500)
        return _JobPageValidation(
            sufficient=sufficient,
            definitive_inactive=False,
            reason=None if sufficient else "Missing title, JD, or apply signals.",
            signals=signals,
            red_flags=red_flags,
        )

    def _is_generic_redirect(self, original_url: str, final_url: str | None) -> bool:
        if not final_url:
            return False
        original = urlparse(original_url)
        final = urlparse(final_url)
        if original.netloc != final.netloc:
            return False
        original_path = original.path.rstrip("/").lower()
        final_path = final.path.rstrip("/").lower()
        if original_path == final_path:
            return False
        return final_path in self.generic_paths

    def _is_security_challenge(self, final_url: str | None, text: str) -> bool:
        final_path = urlparse(final_url or "").path.lower()
        if any(path in final_path for path in self.security_challenge_paths):
            return True
        return self._contains_any(text, self.security_challenge_keywords)

    def _looks_like_job_title(self, title: str) -> bool:
        if not title or len(title) < 4:
            return False
        generic = ("招聘", "职位搜索", "jobs", "careers", "login", "sign in")
        if title.lower() in generic:
            return False
        title_keywords = (
            "工程师",
            "开发",
            "算法",
            "产品",
            "运营",
            "数据",
            "设计",
            "经理",
            "实习",
            "顾问",
            "analyst",
            "engineer",
            "developer",
            "manager",
            "specialist",
            "designer",
            "intern",
            "architect",
            "consultant",
        )
        return self._contains_any(title, title_keywords) or len(title) >= 8

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        lower = text.lower()
        return any(keyword.lower() in lower for keyword in keywords)

    def _count_keyword_hits(self, text: str, keywords: tuple[str, ...]) -> int:
        lower = text.lower()
        return sum(1 for keyword in keywords if keyword.lower() in lower)

    def _clean_text(self, value: Any) -> str:
        if not value:
            return ""
        if hasattr(value, "get_text"):
            value = value.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", str(value)).strip()

    def _normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    def _stringify_json_value(self, value: Any) -> str:
        if not value:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    def _failure_message(self, result: JobCrawlResult) -> str:
        reason = result.failure_reason or "unknown reason"
        return f"{result.source}: {reason}"

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = value.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            result.append(cleaned)
        return result
