"""Ollama ローカル LLM プロバイダー。

Ollama は OpenAI 互換 API (/v1/chat/completions) を提供しているため、
OpenAIProvider を base_url のみ変えて再利用する。

前提: Ollama がローカルで起動済みであること。
  $ ollama serve
  $ ollama pull llama3.2

Ollama 特有の調整:
  - temperature デフォルト 0.0 (ツール選択の安定性向上)
  - parallel_tool_calls を送信しない (多くのモデルが非対応)
  - ツールあり時のストリーミングは非ストリーミング fallback (出力が不安定)
  - JSON スキーマに additionalProperties:false と required を付与
"""

from collections.abc import Iterator
from copy import deepcopy
from typing import Any

from ptsu_code.agent.providers.base import LLMResponse, LLMStreamChunk
from ptsu_code.agent.providers.openai_provider import OpenAIProvider

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_TEMPERATURE = 0.0


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

    @staticmethod
    def _normalize_tools(
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]] | None:
        """Ollama 向けにツールスキーマを正規化する。

        各ツールの parameters に additionalProperties:false と
        required (全プロパティ名) を付与することで、
        ローカルモデルの出力を制約し Tool Calling を安定させる。

        Args:
            tools: OpenAI 形式のツールリスト

        Returns:
            正規化済みツールリスト。None の場合は None をそのまま返す。
        """
        if not tools:
            return tools

        normalized = []
        for tool in deepcopy(tools):
            if tool.get("type") != "function":
                normalized.append(tool)
                continue

            params: dict[str, Any] = tool.get("function", {}).get("parameters", {})
            if params.get("type") == "object":
                params.setdefault("additionalProperties", False)
                props = params.get("properties", {})
                if props and "required" not in params:
                    params["required"] = list(props.keys())

            normalized.append(tool)
        return normalized

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """Ollama 向け調整を施したチャット補完。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ。None の場合は DEFAULT_OLLAMA_TEMPERATURE を使用
            model: モデル名

        Returns:
            LLMレスポンス
        """
        return super().chat(
            messages=messages,
            tools=self._normalize_tools(tools),
            temperature=temperature if temperature is not None else DEFAULT_OLLAMA_TEMPERATURE,
            model=model,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> Iterator[LLMStreamChunk]:
        """Ollama 向け調整を施したストリーミング補完。

        ツールが指定されている場合は、ストリーミングが不安定なため
        非ストリーミングの chat() にフォールバックする。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ。None の場合は DEFAULT_OLLAMA_TEMPERATURE を使用
            model: モデル名

        Yields:
            ストリーミングチャンク
        """
        effective_temp = temperature if temperature is not None else DEFAULT_OLLAMA_TEMPERATURE
        normalized_tools = self._normalize_tools(tools)

        if normalized_tools:
            response = super().chat(
                messages=messages,
                tools=normalized_tools,
                temperature=effective_temp,
                model=model,
            )
            yield LLMStreamChunk(
                content_delta=response.content,
                is_final=True,
                final_response=response,
            )
            return

        yield from super().stream(
            messages=messages,
            tools=None,
            temperature=effective_temp,
            model=model,
        )
