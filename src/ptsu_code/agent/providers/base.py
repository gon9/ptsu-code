"""LLMプロバイダーの基底クラス。"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """LLM応答。"""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"


@dataclass
class LLMStreamChunk:
    """ストリーミングチャンク。"""

    content_delta: str = ""
    tool_calls_delta: list[dict[str, Any]] | None = None
    is_final: bool = False
    final_response: LLMResponse | None = None


class LLMProvider(ABC):
    """LLMプロバイダーの基底クラス。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        """チャット補完を実行する。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ
            model: モデル名

        Returns:
            LLM応答
        """
        pass

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> Iterator[LLMStreamChunk]:
        """ストリーミングでチャット補完を実行する。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ
            model: モデル名

        Yields:
            ストリーミングチャンク

        Note:
            デフォルト実装は非ストリーミング（chat()を呼び出して一括返却）
            各プロバイダーで必要に応じてオーバーライドする
        """
        response = self.chat(messages, tools, temperature, model)
        yield LLMStreamChunk(
            content_delta=response.content,
            is_final=True,
            final_response=response,
        )
