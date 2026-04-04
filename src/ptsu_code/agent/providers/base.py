"""LLMプロバイダーの基底クラス。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """LLMレスポンス。"""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    stop_reason: str = "stop"


class LLMProvider(ABC):
    """LLMプロバイダーの基底クラス。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> LLMResponse:
        """チャット補完を実行する。

        Args:
            messages: メッセージリスト
            tools: ツール定義リスト
            temperature: 温度パラメータ
            model: モデル名

        Returns:
            LLMレスポンス
        """
        pass
