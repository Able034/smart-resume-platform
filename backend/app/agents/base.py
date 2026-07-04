import os
import logging
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda


from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseAgent:
    load_dotenv(override=True)
    os.environ.pop("SSLKEYLOGFILE", None)


    system_prompt: str = ""
    llm_max_attempts: int = 3

    def __init__(self, allow_fallback: bool = True):
        self.allow_fallback = allow_fallback

    def should_use_mock(self) -> bool:
        api_key = os.getenv("CLIKEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        return settings.llm_mock or not api_key

    def raise_real_llm_required(self) -> None:
        api_key = os.getenv("CLIKEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        if settings.llm_mock:
            raise RuntimeError("Real LLM is required, but LLM_MOCK is true.")
        if not api_key:
            raise RuntimeError("Real LLM is required, but no API key is configured.")
        raise RuntimeError("Real LLM is required, but the agent is in mock mode.")

    def build_llm(self, temperature: float = 0.7):
        api_key = os.getenv("CLIKEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        base_url = os.getenv("CLIBASEURL")
        model = os.getenv("OPENAI_MODEL") or settings.openai_model
        timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        if not base_url:
            raise RuntimeError("CLIBASEURL is required for LLM calls.")

        endpoint_mode = os.getenv("LLM_ENDPOINT_MODE", "openai_compatible").strip().lower()
        endpoint = self._resolve_llm_endpoint(base_url, endpoint_mode)

        return RunnableLambda(
            lambda prompt_value: self._invoke_direct_llm(
                prompt_value=prompt_value,
                endpoint=endpoint,
                endpoint_mode=endpoint_mode,
                api_key=api_key,
                model=model,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )
        )

    def _resolve_llm_endpoint(self, base_url: str, endpoint_mode: str) -> str:
        normalized = base_url.rstrip("/")
        if endpoint_mode == "direct":
            return normalized
        if endpoint_mode not in {"openai", "openai_compatible", "openai-compatible"}:
            raise RuntimeError(
                "LLM_ENDPOINT_MODE must be openai_compatible or direct."
            )
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"

    def _invoke_direct_llm(
        self,
        prompt_value: Any,
        endpoint: str,
        endpoint_mode: str,
        api_key: str | None,
        model: str,
        temperature: float,
        timeout_seconds: float,
    ) -> AIMessage:
        messages = self._prompt_value_to_messages(prompt_value)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info(
            "LLM HTTP request mode=%s endpoint=%s model=%s",
            endpoint_mode,
            endpoint,
            model,
        )
        response = httpx.post(
            endpoint,
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        content = self._extract_direct_llm_content(response)
        return AIMessage(content=content)

    def _prompt_value_to_messages(self, prompt_value: Any) -> list[dict[str, str]]:
        if hasattr(prompt_value, "to_messages"):
            raw_messages = prompt_value.to_messages()
        elif isinstance(prompt_value, list):
            raw_messages = prompt_value
        else:
            raw_messages = [prompt_value]

        messages: list[dict[str, str]] = []
        for message in raw_messages:
            role = getattr(message, "type", "user")
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
            elif role not in {"system", "user", "assistant", "tool"}:
                role = "user"
            content = getattr(message, "content", message)
            messages.append({"role": role, "content": self._stringify_message_content(content)})
        return messages

    def _stringify_message_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or item))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    def _extract_direct_llm_content(self, response: httpx.Response) -> str:
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return response.text

        payload = response.json()
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, dict):
            return str(payload)

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and message.get("content") is not None:
                    return str(message["content"])
                if first.get("text") is not None:
                    return str(first["text"])

        for key in ("content", "text", "response", "result", "output"):
            value = payload.get(key)
            if value is not None:
                return str(value)

        raise RuntimeError(f"Unsupported direct LLM response format: {payload}")

    def invoke_with_retries(
        self,
        runnable: Any,
        payload: dict[str, Any],
        max_attempts: int | None = None,
    ) -> Any:
        attempts = max_attempts or self.llm_max_attempts
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started_at = time.perf_counter()
            timeout_seconds = os.getenv("LLM_TIMEOUT_SECONDS", "60")
            logger.info(
                "%s LLM call attempt %s/%s started. timeout=%ss fallback=%s",
                self.__class__.__name__,
                attempt,
                attempts,
                timeout_seconds,
                self.allow_fallback,
            )
            try:
                response = runnable.invoke(payload)
                elapsed = time.perf_counter() - started_at
                logger.info(
                    "%s LLM call attempt %s/%s succeeded in %.2fs.",
                    self.__class__.__name__,
                    attempt,
                    attempts,
                    elapsed,
                )
                return response
            except Exception as exc:
                elapsed = time.perf_counter() - started_at
                last_error = exc
                if attempt >= attempts:
                    logger.exception(
                        "%s LLM call failed after %s attempts. Last attempt took %.2fs.",
                        self.__class__.__name__,
                        attempts,
                        elapsed,
                    )
                    break
                delay_seconds = min(2 ** (attempt - 1), 4)
                logger.warning(
                    "%s LLM call failed on attempt %s/%s after %.2fs, retrying in %ss: %s",
                    self.__class__.__name__,
                    attempt,
                    attempts,
                    elapsed,
                    delay_seconds,
                    exc,
                )
                time.sleep(delay_seconds)
        if last_error:
            raise last_error
        raise RuntimeError("LLM call failed without an exception.")
