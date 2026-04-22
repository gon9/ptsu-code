"""Anthropic LLMプロバイダー。"""

import json
from collections.abc import Iterator
from typing import Any

from anthropic import Anthropic

from .base import LLMProvider, LLMResponse, LLMStreamChunk


class AnthropicProvider(LLMProvider):
    """Anthropic APIプロバイダー。"""

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-5") -> None:
        """初期化。

        Args:
            api_key: Anthropic APIキー
            default_model: デフォルトモデル
        """
        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model

    def _convert_messages(self, messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """メッセージをAnthropic形式に変換する。

        OpenAI形式 → Anthropic形式の変換:
        - role="system" → system_promptとして分離
        - role="assistant" + tool_calls → content: [{type: tool_use, ...}]
        - role="tool" (連続) → role="user" + content: [{type: tool_result, ...}]

        Args:
            messages: OpenAI形式のメッセージリスト

        Returns:
            (system_prompt, messages)のタプル
        """
        system_prompt = ""
        converted: list[dict[str, Any]] = []

        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "system":
                system_prompt = msg["content"]
                i += 1
                continue

            if role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    content_blocks: list[dict[str, Any]] = []
                    if msg.get("content"):
                        content_blocks.append({"type": "text", "text": msg["content"]})
                    for tc in tool_calls:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]),
                        })
                    converted.append({"role": "assistant", "content": content_blocks})
                else:
                    converted.append({"role": "assistant", "content": msg["content"]})
                i += 1
                continue

            if role == "tool":
                tool_results: list[dict[str, Any]] = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tm = messages[i]
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tm["tool_call_id"],
                        "content": tm["content"],
                    })
                    i += 1
                converted.append({"role": "user", "content": tool_results})
                continue

            converted.append({"role": role, "content": msg["content"]})
            i += 1

        return system_prompt, converted

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
        temperature: float | None = None,
        model: str | None = None,
        thinking_budget: int | None = None,
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

        max_tokens = 4096
        if thinking_budget is not None:
            max_tokens = max(16000, thinking_budget * 2)

        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
        }
        if thinking_budget is not None:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        elif temperature is not None:
            kwargs["temperature"] = temperature

        if system_prompt:
            kwargs["system"] = system_prompt

        if converted_tools:
            kwargs["tools"] = converted_tools

        response = self.client.messages.create(**kwargs)

        content = ""
        tool_calls = None

        for block in response.content:
            if block.type == "thinking":
                pass
            elif block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []

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
            finish_reason=response.stop_reason,
        )

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        model: str | None = None,
        thinking_budget: int | None = None,
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

        # Anthropic形式に変換
        system_prompt, converted_messages = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools)

        max_tokens = 4096
        if thinking_budget is not None:
            max_tokens = max(16000, thinking_budget * 2)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if thinking_budget is not None:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        elif temperature is not None:
            kwargs["temperature"] = temperature

        if system_prompt:
            kwargs["system"] = system_prompt

        if converted_tools:
            kwargs["tools"] = converted_tools

        stream = self.client.messages.create(**kwargs)

        content_parts = []
        tool_calls_parts: dict[str, dict] = {}

        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "text":
                    pass  # テキストブロック開始
                elif event.content_block.type == "tool_use":
                    # ツール使用ブロック開始
                    tool_id = event.content_block.id
                    tool_calls_parts[tool_id] = {
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": event.content_block.name,
                            "arguments": "",
                        },
                    }

            elif event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    # テキストの差分
                    content_delta = event.delta.text
                    content_parts.append(content_delta)
                    yield LLMStreamChunk(content_delta=content_delta)

                elif event.delta.type == "input_json_delta":
                    # ツール入力の差分
                    # Anthropicは最後のツールIDを追跡する必要がある
                    if tool_calls_parts:
                        last_tool_id = list(tool_calls_parts.keys())[-1]
                        tool_calls_parts[last_tool_id]["function"]["arguments"] += event.delta.partial_json

            elif event.type == "message_delta":
                # メッセージ完了
                if event.delta.stop_reason:
                    tool_calls = list(tool_calls_parts.values()) if tool_calls_parts else None
                    final_response = LLMResponse(
                        content="".join(content_parts),
                        tool_calls=tool_calls,
                        finish_reason=event.delta.stop_reason,
                    )
                    yield LLMStreamChunk(
                        is_final=True,
                        final_response=final_response,
                    )
