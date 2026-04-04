"""Anthropicプロバイダー。"""

from typing import Any

from anthropic import Anthropic

from .base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic APIプロバイダー。"""

    def __init__(self, api_key: str, default_model: str = "claude-3-5-sonnet-20241022") -> None:
        """初期化。

        Args:
            api_key: Anthropic APIキー
            default_model: デフォルトモデル
        """
        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model

    def _convert_messages(self, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """メッセージをAnthropic形式に変換する。

        Args:
            messages: OpenAI形式のメッセージリスト

        Returns:
            (system_prompt, messages)のタプル
        """
        system_prompt = ""
        converted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                converted_messages.append(msg)

        return system_prompt, converted_messages

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """ツールをAnthropic形式に変換する。

        Args:
            tools: OpenAI形式のツールリスト

        Returns:
            Anthropic形式のツールリスト
        """
        if not tools:
            return None

        converted_tools = []
        for tool in tools:
            if tool["type"] == "function":
                func = tool["function"]
                converted_tools.append(
                    {
                        "name": func["name"],
                        "description": func["description"],
                        "input_schema": func["parameters"],
                    }
                )

        return converted_tools

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
        system_prompt, converted_messages = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools)

        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": converted_messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if converted_tools:
            kwargs["tools"] = converted_tools

        response = self.client.messages.create(**kwargs)

        content = ""
        tool_calls = None

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []

                import json

                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    }
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
        )
