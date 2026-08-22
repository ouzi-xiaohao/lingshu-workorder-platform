from unittest.mock import AsyncMock, patch

import pytest

from src.ai_services.llm_summary import LLMSummaryService
from src.common.circuit_breaker import CircuitState, circuits
from src.tasks.ai_tasks import enrich_work_order
from src.tasks.celery_app import celery_app


@pytest.mark.asyncio
async def test_llm_summary_falls_back_to_rules():
    text = await LLMSummaryService().summarize("北门路灯闪烁后熄灭", ["照明设施"])
    assert "路灯" in text or "照明" in text


@pytest.mark.asyncio
async def test_llm_circuit_falls_back_when_remote_fails(monkeypatch):
    from src.core.config import settings

    monkeypatch.setattr(settings, "ai_mode", "local")
    monkeypatch.setattr(settings, "llm_api_url", "http://llm.invalid/summary")
    circuits.get("ai-llm").failure_threshold = 1

    failing = AsyncMock()
    failing.__aenter__.return_value = failing
    failing.__aexit__.return_value = False
    failing.post = AsyncMock(side_effect=RuntimeError("llm down"))
    with patch("src.ai_services.llm_summary.httpx.AsyncClient", return_value=failing):
        first = await LLMSummaryService().summarize("积水严重")
        second = await LLMSummaryService().summarize("积水严重")
    assert first
    assert second
@pytest.mark.asyncio
async def test_llm_switches_to_backup_model_when_primary_fails(monkeypatch):
    from src.core.config import settings

    monkeypatch.setattr(settings, "ai_mode", "local")
    monkeypatch.setattr(settings, "llm_api_url", "http://llm-primary/summary")
    monkeypatch.setattr(settings, "llm_model", "qwen")
    monkeypatch.setattr(settings, "llm_fallback_model", "qwen-lite")
    circuits.get("ai-llm").failure_threshold = 1

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"summary": "备用模型摘要：地下车库积水"}

    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False

    async def post(url, json=None, headers=None):
        if json and json.get("model") == "qwen-lite":
            return _Response()
        raise RuntimeError("primary llm down")

    client.post = post
    with patch("src.ai_services.llm_summary.httpx.AsyncClient", return_value=client):
        text = await LLMSummaryService().summarize("积水严重")
    assert "备用模型" in text
    assert circuits.get("ai-llm").state is CircuitState.OPEN
    assert circuits.get("ai-llm-backup").state is CircuitState.CLOSED


def test_celery_ai_task_uses_backoff_and_qos():
    assert enrich_work_order.max_retries == 3
    assert enrich_work_order.rate_limit == "20/m"
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_default_delivery_mode == 2
    assert "drain-ai-every-2-minutes" in celery_app.conf.beat_schedule
