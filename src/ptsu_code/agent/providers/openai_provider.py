"""OpenAI LLMプロバイダー。"""

from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from .base import LLMProvider, LLMResponse, LLMStreamChunk


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
            finish_reason=response.choices[0].finish_reason,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
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
        """
        model = model or self.default_model

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools

        stream = self.client.chat.completions.create(**kwargs)

        content_parts = []
        tool_calls_parts: dict[int, dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta

            # コンテンツの差分
            content_delta = delta.content or ""
            if content_delta:
                content_parts.append(content_delta)
                yield LLMStreamChunk(content_delta=content_delta)

            # ツール呼び出しの差分
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index
                    if idx not in tool_calls_parts:
                        tool_calls_parts[idx] = {
                            "id": tool_call_delta.id or "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }

                    if tool_call_delta.id:
                        tool_calls_parts[idx]["id"] = tool_call_delta.id

                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            tool_calls_parts[idx]["function"]["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            tool_calls_parts[idx]["function"]["arguments"] += tool_call_delta.function.arguments

            # 最終チャンク
            if chunk.choices[0].finish_reason:
                tool_calls = list(tool_calls_parts.values()) if tool_calls_parts else None
                final_response = LLMResponse(
                    content="".join(content_parts),
                    tool_calls=tool_calls,
                    finish_reason=chunk.choices[0].finish_reason,
                )
                yield LLMStreamChunk(
                    is_final=True,
                    final_response=final_response,
                )
