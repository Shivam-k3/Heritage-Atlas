"""Bounded Gemini generation for grounded heritage responses."""

from __future__ import annotations

from collections import deque
from threading import BoundedSemaphore, Lock
from time import monotonic

from . import config


class AIProviderError(RuntimeError):
    """The configured AI provider could not produce a safe response."""


class AIRateLimitError(RuntimeError):
    """The local per-process AI request budget has been exhausted."""


class GeminiProvider:
    """Small adapter around the official Google GenAI SDK.

    The SDK is imported lazily so the backend remains usable when AI is disabled and
    the existing CLIP/MiniLM test suite does not need the optional client.
    """

    def __init__(self) -> None:
        self._timestamps: deque[float] = deque()
        self._lock = Lock()
        self._concurrency = BoundedSemaphore(config.ai_max_concurrency())

    def status(self) -> dict[str, object]:
        configured = (
            config.ai_enabled()
            and config.ai_provider() == "gemini"
            and config.gemini_api_key() is not None
        )
        return {
            "enabled": config.ai_enabled(),
            "provider": config.ai_provider(),
            "model": config.gemini_model(),
            "configured": configured,
            "available": configured,
        }

    def generate(self, system_instruction: str, prompt: str) -> str:
        if not config.ai_enabled():
            raise AIProviderError("AI assistant is disabled")
        if config.ai_provider() != "gemini":
            raise AIProviderError("configured AI provider is unsupported")
        api_key = config.gemini_api_key()
        if not api_key:
            raise AIProviderError("Gemini API key is not configured")
        self._check_rate_limit()
        if not self._concurrency.acquire(timeout=config.ai_timeout_seconds()):
            raise AIProviderError("AI generation concurrency limit reached")
        try:
            response = self._request_with_retries(api_key, system_instruction, prompt)
        finally:
            self._concurrency.release()

        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("Gemini returned an empty response")
        return text.strip()

    def _request_with_retries(self, api_key: str, system_instruction: str, prompt: str) -> object:
        from google import genai
        from google.genai import types

        for attempt in range(config.ai_max_retries() + 1):
            try:
                client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(
                        timeout=int(config.ai_timeout_seconds() * 1_000)
                    ),
                )
                return client.models.generate_content(
                    model=config.gemini_model(),
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=config.ai_temperature(),
                        max_output_tokens=config.ai_max_output_tokens(),
                    ),
                )
            except (TimeoutError, ConnectionError) as exc:
                if attempt >= config.ai_max_retries():
                    raise AIProviderError(f"Gemini request failed: {type(exc).__name__}") from exc
            except Exception as exc:
                raise AIProviderError(f"Gemini request failed: {type(exc).__name__}") from exc
        raise AIProviderError("Gemini request failed")

    def _check_rate_limit(self) -> None:
        now = monotonic()
        with self._lock:
            while self._timestamps and now - self._timestamps[0] >= 60:
                self._timestamps.popleft()
            if len(self._timestamps) >= config.ai_max_requests_per_minute():
                raise AIRateLimitError("AI request rate limit reached")
            self._timestamps.append(now)


provider = GeminiProvider()


def generate(system_instruction: str, prompt: str) -> str:
    """Generate one bounded response through the configured provider."""
    return provider.generate(system_instruction, prompt)


def status() -> dict[str, object]:
    return provider.status()
