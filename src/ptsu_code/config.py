"""設定管理モジュール。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROVIDER_MODELS: dict[str, dict[str, str]] = {
    "openai": {
        "fast": "gpt-5-mini",
        "smart": "gpt-4o",
    },
    "anthropic": {
        "fast": "claude-haiku-4-5",
        "smart": "claude-sonnet-4-5",
    },
    "ollama": {
        "fast": "llama3.2",
        "smart": "llama3.1",
    },
}


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
    openai_model_fast: str = "gpt-5-mini"
    openai_model_smart: str = "gpt-4o"
    anthropic_model_fast: str = "claude-haiku-4-5"
    anthropic_model_smart: str = "claude-sonnet-4-5"
    history_dir: Path = Path.home() / ".ptsu" / "history"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model_fast: str = "llama3.2"
    ollama_model_smart: str = "llama3.1"


settings = Settings()


def get_model(provider: str, tier: str = "fast") -> str:
    """プロバイダーとティアからモデル名を解決する。

    Args:
        provider: LLMプロバイダー名 ('openai' or 'anthropic')
        tier: モデルティア ('fast' or 'smart')

    Returns:
        モデル名
    """
    tier_map: dict[str, dict[str, str]] = {
        "openai": {
            "fast": settings.openai_model_fast,
            "smart": settings.openai_model_smart,
        },
        "anthropic": {
            "fast": settings.anthropic_model_fast,
            "smart": settings.anthropic_model_smart,
        },
        "ollama": {
            "fast": settings.ollama_model_fast,
            "smart": settings.ollama_model_smart,
        },
    }
    return tier_map.get(provider, tier_map["openai"]).get(tier, settings.openai_model_fast)
