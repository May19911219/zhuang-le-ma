from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = SERVER_ROOT / "data"
ENV_PATH = SERVER_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "claude-sonnet-4-5"
    admin_password: str = "zhuang-le-ma"
    database_url: str = f"sqlite:///{(DATA_DIR / 'zhuang.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """读取服务端配置，结果会缓存到进程内。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()


def clear_settings_cache() -> None:
    """清掉配置缓存，便于测试或重新导入密钥后立即生效。"""
    get_settings.cache_clear()
