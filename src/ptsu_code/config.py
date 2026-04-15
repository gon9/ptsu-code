"""設定管理モジュール。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。"""

    model_config = SettingsConfigDict(
        env_prefix="PTSU_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ptsu"
    version: str = "0.1.0"
    verbose: bool = False
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "openai"
    openai_model: str = "gpt-5-mini"
    anthropic_model: str = "claude-sonnet-4-5"
    history_dir: Path = Path.home() / ".ptsu" / "history"


settings = Settings()
