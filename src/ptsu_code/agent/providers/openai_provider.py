"""OpenAIプロバイダー。"""

from typing import Any

from openai import OpenAI

from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI APIプロバイダー。"""

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini") -> None:
        """初期化。

        Args:
            api_key: OpenAI APIキー
            default_model: デフォルトモデル
        """
        self.client = OpenAI(api_key=api_key)
        self.default_model = default_model

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
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,  # type: ignore
            tools=tools,  # type: ignore
            temperature=temperature,
        )

        message = response.choices[0].message
        tool_calls = None

        if message.tool_calls:
            tool_calls = [tc.model_dump() for tc in message.tool_calls]

        return LLMResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            stop_reason=response.choices[0].finish_reason or "stop",
        )
