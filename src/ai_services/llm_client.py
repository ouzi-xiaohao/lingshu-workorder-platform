from __future__ import annotations

import json
import re
from typing import Any

import httpx

from src.agent.intent_rules import classify_intent_rules
from src.common.circuit_breaker import circuits
from src.core.config import settings


class LLMClient:
    """OpenAI-compatible chat client with rule fallback."""

    async def classify_intent(
        self,
        text: str,
        *,
        area: str = "未知区域",
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        fallback = classify_intent_rules(text, area=area, evidence=evidence)
        if settings.ai_mode not in {"local", "production"} or not settings.llm_api_url:
            return fallback

        async def primary():
            return await self._classify(settings.llm_api_url, settings.llm_model, settings.llm_api_key, text, area, evidence or [])

        async def backup():
            backup_url = settings.llm_fallback_api_url or settings.llm_api_url
            backup_model = settings.llm_fallback_model
            if not backup_model or (backup_model == settings.llm_model and backup_url == settings.llm_api_url):
                return fallback

            async def backup_call():
                return await self._classify(
                    backup_url,
                    backup_model,
                    settings.llm_fallback_api_key or settings.llm_api_key,
                    text,
                    area,
                    evidence or [],
                )

            return await circuits.get("ai-llm-backup").execute(backup_call, lambda: fallback)

        return await circuits.get("ai-llm").execute(primary, backup)

    async def _classify(
        self,
        url: str,
        model: str,
        api_key: str,
        text: str,
        area: str,
        evidence: list[str],
    ) -> dict[str, Any]:
        categories = ("暖通空调", "设备故障", "照明设施", "安全隐患", "环境卫生", "综合服务")
        evidence_block = "\n".join(f"- {item}" for item in evidence[:12]) or "- 无额外证据"
        system = (
            "你是工单意图分类器。综合文字与多模态证据输出 JSON：category, priority, confidence, rationale。"
            f"category 只能是 {categories} 之一；priority 只能是 紧急/高/中；confidence 为 0~1 小数。"
            "若视觉/语音证据与文字冲突，安全类（安全隐患）优先。"
        )
        user = f"区域：{area}\n工单摘要：{text}\n多模态证据：\n{evidence_block}"
        payload = await self._chat(
            url,
            model,
            api_key,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            timeout=settings.llm_intent_timeout_seconds,
        )
        parsed = self._parse_json(payload)
        category = str(parsed.get("category") or "综合服务")
        if category not in categories:
            raise ValueError(f"invalid category: {category}")
        priority = str(parsed.get("priority") or "中")
        if priority not in {"紧急", "高", "中"}:
            priority = "中"
        confidence = max(0.0, min(0.99, float(parsed.get("confidence") or 0.5)))
        return {
            "category": category,
            "priority": priority,
            "confidence": round(confidence, 2),
            "tags": [category, priority, area],
            "intent_source": "llm",
            "rationale": str(parsed.get("rationale") or "")[:200],
        }

    async def _chat(
        self,
        url: str,
        model: str,
        api_key: str,
        messages: list[dict[str, str]],
        *,
        timeout: float,
    ) -> str:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        body = {"model": model, "messages": messages, "temperature": 0}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            payload = response.json()
        if "choices" in payload:
            message = payload["choices"][0]["message"]
            return str(message.get("content") or "").strip()
        return str(payload.get("content") or payload.get("summary") or "").strip()

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)


llm_client = LLMClient()
