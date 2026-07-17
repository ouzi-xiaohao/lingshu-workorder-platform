from dataclasses import dataclass

from src.core.config import settings


@dataclass
class LLMResult:
    text: str
    provider: str
    degraded: bool = False


class LLMClient:
    async def complete(self, prompt: str) -> LLMResult:
        if settings.ai_mode == "fallback" or not settings.llm_api_url:
            return LLMResult(text=prompt[:500], provider="rules", degraded=True)
        # Production deployments can replace this adapter without changing services.
        return LLMResult(text=prompt[:500], provider="remote-api", degraded=False)
