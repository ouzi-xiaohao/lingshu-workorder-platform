from src.core.config import settings


UNSAFE_SECRETS = {"change-me-in-production", "replace-with-a-long-random-secret"}


def validate_runtime_settings(config=settings) -> None:
    if str(config.environment).lower() != "production":
        return
    if config.secret_key in UNSAFE_SECRETS or len(config.secret_key) < 32:
        raise RuntimeError("生产环境必须配置至少 32 位的 SECRET_KEY")
    if config.database_url.startswith("sqlite"):
        raise RuntimeError("生产环境必须使用 PostgreSQL")
