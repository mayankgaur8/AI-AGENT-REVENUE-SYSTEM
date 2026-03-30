import asyncio
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SharedAIError(Exception):
    pass


class SharedAIClient:
    def __init__(self):
        self.base_url = (settings.AI_PLATFORM_URL or "").rstrip("/")
        self.api_key = settings.AI_PLATFORM_API_KEY or ""
        self.timeout_ms = settings.AI_TIMEOUT_MS
        self.require_app_key = settings.AI_REQUIRE_APP_KEY

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def call_ai(
        self,
        *,
        prompt: str,
        prompt_type: str = "general",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        if not self.base_url:
            raise SharedAIError("AI platform URL is not configured")
        if self.require_app_key and not self.api_key:
            raise SharedAIError("AI platform API key is required but missing")

        payload = {
            "prompt": prompt,
            "type": prompt_type,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_ms / 1000.0) as client:
                    response = await client.post(f"{self.base_url}/v1/generate", json=payload, headers=headers)

                if response.status_code == 401:
                    raise SharedAIError("Unauthorized by shared AI platform")
                if response.status_code >= 500:
                    raise SharedAIError(f"Shared AI platform upstream failure ({response.status_code})")
                response.raise_for_status()

                data = response.json()
                reply = (
                    data.get("reply")
                    or data.get("text")
                    or data.get("response")
                    or data.get("content")
                    or ""
                )
                if not isinstance(reply, str) or not reply.strip():
                    raise SharedAIError("Shared AI platform returned an invalid reply payload")

                return {
                    "reply": reply.strip(),
                    "usage": data.get("usage") or {},
                    "model": data.get("model") or data.get("provider") or "",
                }
            except (httpx.TimeoutException, httpx.HTTPError, SharedAIError, ValueError) as exc:
                last_error = exc
                should_retry = isinstance(exc, (httpx.TimeoutException, httpx.HTTPError, SharedAIError))
                is_final_attempt = attempt == 2
                if isinstance(exc, SharedAIError) and "Unauthorized" in str(exc):
                    break
                if not should_retry or is_final_attempt:
                    break
                await asyncio.sleep(0.5 * (attempt + 1))

        logger.error("Shared AI request failed: %s", last_error)
        raise SharedAIError(str(last_error) if last_error else "Shared AI request failed")
