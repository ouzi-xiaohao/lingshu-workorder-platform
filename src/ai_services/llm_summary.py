from __future__ import annotations

import httpx

from src.common.circuit_breaker import circuits
from src.core.config import settings


class LLMSummaryService:
    async def summarize(self, text: str, evidence: list[str] | None = None) -> str:
        rules = self._rule_summary(text, evidence or [])
        if settings.ai_mode not in {"local", "production"} or not settings.llm_api_url:
            return rules

        async def primary():
            return await self._complete(settings.llm_api_url, settings.llm_model, settings.llm_api_key, text, evidence or [])

        async def backup():
            backup_url = settings.llm_fallback_api_url or settings.llm_api_url
            backup_model = settings.llm_fallback_model
            if not backup_model or (backup_model == settings.llm_model and backup_url == settings.llm_api_url):
                return rules

            async def backup_call():
                return await self._complete(
                    backup_url,
                    backup_model,
                    settings.llm_fallback_api_key or settings.llm_api_key,
                    text,
                    evidence or [],
                )

            return await circuits.get("ai-llm-backup").execute(backup_call, lambda: rules)

        return await circuits.get("ai-llm").execute(primary, backup)

    async def _complete(self, url: str, model: str, api_key: str, text: str, evidence: list[str]) -> str:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                url,
                json={"model": model, "text": text, "evidence": evidence},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
        summary = str(payload.get("summary") or payload.get("content") or "").strip()
        if not summary:
            raise RuntimeError("empty llm summary")
        return summary[:400]

    def _rule_summary(self, text: str, evidence: list[str]) -> str:
        parts = [item.strip() for item in [text, *evidence] if item and str(item).strip()]
        compact: list[str] = []
        seen: set[str] = set()
        for part in parts:
            normalized = " ".join(str(part).split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                compact.append(normalized)
        return "；".join(compact)[:180]
