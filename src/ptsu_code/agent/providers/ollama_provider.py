"""Ollama ローカル LLM プロバイダー。

Ollama は OpenAI 互換 API (/v1/chat/completions) を提供しているため、
OpenAIProvider を base_url のみ変えて再利用する。

前提: Ollama がローカルで起動済みであること。
  $ ollama serve
  $ ollama pull llama3.2
"""

from ptsu_code.agent.providers.openai_provider import OpenAIProvider

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.2"


class OllamaProvider(OpenAIProvider):
    """Ollama ローカル LLM プロバイダー。

    OpenAI 互換エンドポイントを使用するため、
    Tool Calling に対応したモデル（llama3.1, llama3.2 等）が必要。
    """

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        default_model: str = DEFAULT_OLLAMA_MODEL,
    ) -> None:
        """初期化。

        Args:
            base_url: Ollama API エンドポイント。デフォルトは localhost:11434
            default_model: 使用するモデル名。デフォルトは llama3.2
        """
        super().__init__(
            api_key="ollama",
            default_model=default_model,
            base_url=base_url,
        )
