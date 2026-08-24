from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "灵枢智能工单协同调度平台"
    app_version: str = "1.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 120
    database_url: str = "sqlite+aiosqlite:///./data/lingshu.db"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "workorder-media"
    minio_secure: bool = False
    media_storage_mode: str = "auto"
    local_media_dir: str = "data/media"
    max_upload_bytes: int = 50 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    rate_limit_per_minute: int = 120
    ai_mode: str = "fallback"
    ai_async_enabled: bool = True
    whisper_model: str = "base"
    yolo_model: str = "yolov8n.pt"
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "qwen"
    llm_fallback_api_url: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_model: str = ""
    circuit_failure_threshold: int = 5
    circuit_recovery_seconds: float = 30
    circuit_half_open_max_calls: int = 1
    cache_l1_ttl_seconds: int = 5
    cache_l2_ttl_seconds: int = 30
    cache_ttl_jitter_ratio: float = 0.2
    cache_max_l1_items: int = 2048
    agent_pipeline: str = "work-order-agent"
    intent_human_review_threshold: float = 0.85
    llm_intent_timeout_seconds: float = 8.0
    patrol_backlog_threshold: int = 20
    patrol_utilization_threshold: float = 0.85
    patrol_hotspot_threshold: int = 10
    ai_enrich_rate_limit: str = "20/m"
    db_pool_size: int = 10
    db_max_overflow: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
