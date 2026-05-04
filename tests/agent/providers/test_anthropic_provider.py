"""AnthropicProviderのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider
from ptsu_code.agent.providers.base import LLMResponse


@pytest.fixture
def mock_anthropic_client():
    """Anthropicクライアントのモック。"""
    with patch("ptsu_code.agent.providers.anthropic_provider.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def provider(mock_anthropic_client):
    """テスト用AnthropicProvider。"""
    return AnthropicProvider(api_key="test-key")


def _make_text_block(text: str):
    """テキストブロックのモックを生成する。"""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_block(tool_id: str, name: str, input_data: dict):
    """ツール使用ブロックのモックを生成する。"""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = name
    block.input = input_data
    return block


def _make_chat_response(blocks: list, stop_reason: str = "end_turn"):
    """Anthropic メッセージレスポンスのモックを生成する。"""
    response = MagicMock()
    response.content = blocks
    response.stop_reason = stop_reason
    return response


class TestAnthropicProviderInit:
    """AnthropicProvider初期化テスト。"""

    def test_init_sets_default_model(self, mock_anthropic_client):
        """デフォルトモデルが設定されることを確認する。"""
        p = AnthropicProvider(api_key="key")
        assert p.default_model == "claude-sonnet-4-5"

    def test_init_custom_model(self, mock_anthropic_client):
        """カスタムモデルが設定されることを確認する。"""
        p = AnthropicProvider(api_key="key", default_model="claude-3-opus")
        assert p.default_model == "claude-3-opus"


class TestConvertMessages:
    """AnthropicProvider._convert_messagesのテスト。"""

    def test_extracts_system_prompt(self, provider):
        """systemメッセージがsystem_promptとして抽出されることを確認する。"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        system, converted = provider._convert_messages(messages)
        assert system == "You are helpful"
        assert len(converted) == 1
        assert converted[0]["role"] == "user"

    def test_no_system_message(self, provider):
        """systemメッセージなしの場合、空文字列が返されることを確認する。"""
        messages = [{"role": "user", "content": "Hello"}]
        system, converted = provider._convert_messages(messages)
        assert system == ""
        assert len(converted) == 1

    def test_preserves_other_messages(self, provider):
        """user/assistantメッセージが保持されることを確認する。"""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "How are you?"},
        ]
        _, converted = provider._convert_messages(messages)
        assert len(converted) == 3

    def test_assistant_with_tool_calls_converted(self, provider):
        """assistantのtool_callsがAnthropic形式のcontent blocksに変換されること。"""
        import json

        messages = [
            {"role": "user", "content": "read x.py"},
            {
                "role": "assistant",
                "content": "I'll read it.",
                "tool_calls": [
                    {
                        "id": "toolu_1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": json.dumps({"path": "x.py"})},
                    }
                ],
            },
        ]
        _, converted = provider._convert_messages(messages)
        asst = converted[1]
        assert asst["role"] == "assistant"
        assert isinstance(asst["content"], list)
        types = {b["type"] for b in asst["content"]}
        assert "text" in types
        assert "tool_use" in types

    def test_assistant_tool_calls_without_text(self, provider):
        """assistantのcontentが空でもtool_use blockが生成されること。"""
        import json

        messages = [
            {"role": "user", "content": "go"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "toolu_2",
                        "type": "function",
                        "function": {"name": "run", "arguments": json.dumps({})},
                    }
                ],
            },
        ]
        _, converted = provider._convert_messages(messages)
        asst = converted[1]
        blocks = asst["content"]
        assert all(b["type"] == "tool_use" for b in blocks)

    def test_tool_role_messages_consolidated(self, provider):
        """toolロールのメッセージが1つのuserメッセージにまとめられること。"""
        messages = [
            {"role": "user", "content": "do it"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "tc1", "type": "function", "function": {"name": "t", "arguments": "{}"}}],
            },
            {"role": "tool", "content": "result1", "tool_call_id": "tc1", "name": "t"},
            {"role": "tool", "content": "result2", "tool_call_id": "tc2", "name": "t2"},
        ]
        _, converted = provider._convert_messages(messages)
        tool_user = converted[-1]
        assert tool_user["role"] == "user"
        assert isinstance(tool_user["content"], list)
        assert len(tool_user["content"]) == 2
        assert all(b["type"] == "tool_result" for b in tool_user["content"])


class TestConvertTools:
    """AnthropicProvider._convert_toolsのテスト。"""

    def test_none_returns_none(self, provider):
        """Noneを渡すとNoneが返されることを確認する。"""
        assert provider._convert_tools(None) is None

    def test_empty_list_returns_none(self, provider):
        """空リストを渡すとNoneが返されることを確認する。"""
        assert provider._convert_tools([]) is None

    def test_converts_openai_format_to_anthropic(self, provider):
        """OpenAI形式のツールがAnthropic形式に変換されることを確認する。"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        result = provider._convert_tools(tools)
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "read_file"
        assert result[0]["description"] == "Read a file"
        assert "input_schema" in result[0]

    def test_converts_multiple_tools(self, provider):
        """複数のツールが変換されることを確認する。"""
        tools = [
            {"type": "function", "function": {"name": "t1", "description": "d1", "parameters": {}}},
            {"type": "function", "function": {"name": "t2", "description": "d2", "parameters": {}}},
        ]
        result = provider._convert_tools(tools)
        assert result is not None
        assert len(result) == 2


class TestAnthropicProviderChat:
    """AnthropicProvider.chatのテスト。"""

    def test_chat_text_response(self, provider, mock_anthropic_client):
        """テキストレスポンスが正しく返されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response(
            [_make_text_block("Hello!")]
        )
        result = provider.chat([{"role": "user", "content": "Hi"}])
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello!"
        assert result.tool_calls is None

    def test_chat_with_tool_use_block(self, provider, mock_anthropic_client):
        """ツール使用ブロックがOpenAI形式に変換されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response(
            [_make_tool_block("toolu_1", "read_file", {"path": "x.py"})]
        )
        result = provider.chat([{"role": "user", "content": "read x.py"}])
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc["id"] == "toolu_1"
        assert tc["function"]["name"] == "read_file"
        assert '"path"' in tc["function"]["arguments"]

    def test_chat_mixed_text_and_tool(self, provider, mock_anthropic_client):
        """テキストとツール使用が混在するレスポンスが処理されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response(
            [
                _make_text_block("I'll read that file."),
                _make_tool_block("toolu_2", "read_file", {"path": "y.py"}),
            ]
        )
        result = provider.chat([{"role": "user", "content": "read y.py"}])
        assert "I'll read that file." in result.content
        assert result.tool_calls is not None

    def test_chat_system_prompt_passed(self, provider, mock_anthropic_client):
        """systemメッセージがsystemパラメータとして渡されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        provider.chat([
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ])
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs.get("system") == "Be helpful"

    def test_chat_no_system_no_system_kwarg(self, provider, mock_anthropic_client):
        """systemメッセージなしでsystemパラメータが渡されないことを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        provider.chat([{"role": "user", "content": "Hi"}])
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert "system" not in call_kwargs

    def test_chat_with_tools(self, provider, mock_anthropic_client):
        """ツール付きのchatが動作することを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        tools = [{"type": "function", "function": {"name": "t", "description": "d", "parameters": {}}}]
        provider.chat([{"role": "user", "content": "msg"}], tools=tools)
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_kwargs

    def test_chat_stop_reason(self, provider, mock_anthropic_client):
        """stop_reasonが正しく返されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response(
            [_make_text_block("ok")], stop_reason="end_turn"
        )
        result = provider.chat([{"role": "user", "content": "msg"}])
        assert result.finish_reason == "end_turn"

    def test_chat_custom_model(self, provider, mock_anthropic_client):
        """カスタムモデルが渡されることを確認する。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        provider.chat([{"role": "user", "content": "msg"}], model="claude-3-opus")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus"

    def test_chat_thinking_budget_sets_kwargs(self, provider, mock_anthropic_client):
        """thinking_budget 指定時に thinking kwarg と拡張 max_tokens が設定されること。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        provider.chat([{"role": "user", "content": "msg"}], thinking_budget=1000)
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["thinking"]["type"] == "enabled"
        assert call_kwargs["thinking"]["budget_tokens"] == 1000
        assert call_kwargs["max_tokens"] >= 16000

    def test_chat_temperature_sets_kwarg(self, provider, mock_anthropic_client):
        """temperature 指定時に temperature kwarg が設定されること。"""
        mock_anthropic_client.messages.create.return_value = _make_chat_response([_make_text_block("ok")])
        provider.chat([{"role": "user", "content": "msg"}], temperature=0.7)
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    def test_chat_thinking_block_is_skipped(self, provider, mock_anthropic_client):
        """thinking ブロックがコンテンツに含まれないこと。"""
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        mock_anthropic_client.messages.create.return_value = _make_chat_response(
            [thinking_block, _make_text_block("answer")]
        )
        result = provider.chat([{"role": "user", "content": "msg"}])
        assert result.content == "answer"


class TestAnthropicProviderStream:
    """AnthropicProvider.streamのテスト。"""

    def _make_event(self, event_type: str, **kwargs):
        """ストリームイベントのモックを生成する。"""
        event = MagicMock()
        event.type = event_type
        for k, v in kwargs.items():
            setattr(event, k, v)
        return event

    def test_stream_text_content(self, provider, mock_anthropic_client):
        """テキストチャンクが正しくyieldされることを確認する。"""
        text_start = self._make_event("content_block_start")
        text_start.content_block = MagicMock(type="text")

        delta_event = self._make_event("content_block_delta")
        delta_event.delta = MagicMock(type="text_delta", text="Hello")

        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")

        mock_anthropic_client.messages.create.return_value = iter([text_start, delta_event, msg_delta])

        chunks = list(provider.stream([{"role": "user", "content": "hi"}]))
        content_chunks = [c for c in chunks if c.content_delta]
        assert len(content_chunks) == 1
        assert content_chunks[0].content_delta == "Hello"

    def test_stream_final_chunk(self, provider, mock_anthropic_client):
        """最終チャンクが正しく生成されることを確認する。"""
        delta_event = self._make_event("content_block_delta")
        delta_event.delta = MagicMock(type="text_delta", text="World")

        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")

        mock_anthropic_client.messages.create.return_value = iter([delta_event, msg_delta])

        chunks = list(provider.stream([{"role": "user", "content": "hi"}]))
        final_chunks = [c for c in chunks if c.is_final]
        assert len(final_chunks) == 1
        assert final_chunks[0].final_response.finish_reason == "end_turn"

    def test_stream_tool_use_block(self, provider, mock_anthropic_client):
        """ツール使用ブロックがアセンブルされることを確認する。"""
        tool_start = self._make_event("content_block_start")
        cb = MagicMock()
        cb.type = "tool_use"
        cb.id = "toolu_1"
        cb.name = "read_file"
        tool_start.content_block = cb

        input_delta = self._make_event("content_block_delta")
        input_delta.delta = MagicMock(type="input_json_delta", partial_json='{"path":"x.py"}')

        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="tool_use")

        mock_anthropic_client.messages.create.return_value = iter([tool_start, input_delta, msg_delta])

        chunks = list(provider.stream([{"role": "user", "content": "read x.py"}]))
        final = next(c for c in chunks if c.is_final)
        assert final.final_response.tool_calls is not None
        tc = final.final_response.tool_calls[0]
        assert tc["function"]["name"] == "read_file"

    def test_stream_with_system_prompt(self, provider, mock_anthropic_client):
        """systemメッセージ付きのストリームが動作することを確認する。"""
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")
        mock_anthropic_client.messages.create.return_value = iter([msg_delta])

        list(provider.stream([
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "hi"},
        ]))
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs.get("system") == "Be helpful"

    def test_stream_message_delta_without_stop_reason(self, provider, mock_anthropic_client):
        """stop_reasonなしのmessage_deltaが無視されることを確認する。"""
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason=None)

        msg_delta2 = self._make_event("message_delta")
        msg_delta2.delta = MagicMock(stop_reason="end_turn")

        mock_anthropic_client.messages.create.return_value = iter([msg_delta, msg_delta2])

        chunks = list(provider.stream([{"role": "user", "content": "hi"}]))
        final_chunks = [c for c in chunks if c.is_final]
        assert len(final_chunks) == 1

    @pytest.mark.parametrize("event_type", ["message_start", "ping", "content_block_stop"])
    def test_stream_ignores_unknown_events(self, provider, mock_anthropic_client, event_type):
        """未知のイベントタイプが無視されることを確認する。"""
        unknown = self._make_event(event_type)
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")

        mock_anthropic_client.messages.create.return_value = iter([unknown, msg_delta])

        chunks = list(provider.stream([{"role": "user", "content": "hi"}]))
        final_chunks = [c for c in chunks if c.is_final]
        assert len(final_chunks) == 1

    def test_stream_thinking_budget_sets_kwargs(self, provider, mock_anthropic_client):
        """stream() で thinking_budget 指定時に thinking kwarg が設定されること。"""
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")
        mock_anthropic_client.messages.create.return_value = iter([msg_delta])

        list(provider.stream([{"role": "user", "content": "hi"}], thinking_budget=2000))
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["thinking"]["type"] == "enabled"
        assert call_kwargs["thinking"]["budget_tokens"] == 2000
        assert call_kwargs["max_tokens"] >= 16000

    def test_stream_temperature_sets_kwarg(self, provider, mock_anthropic_client):
        """stream() で temperature 指定時に temperature kwarg が設定されること。"""
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")
        mock_anthropic_client.messages.create.return_value = iter([msg_delta])

        list(provider.stream([{"role": "user", "content": "hi"}], temperature=0.5))
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    def test_stream_with_tools_passes_tools_kwarg(self, provider, mock_anthropic_client):
        """stream() でツール指定時に tools kwarg が設定されること。"""
        msg_delta = self._make_event("message_delta")
        msg_delta.delta = MagicMock(stop_reason="end_turn")
        mock_anthropic_client.messages.create.return_value = iter([msg_delta])

        tools = [{"type": "function", "function": {"name": "t", "description": "d", "parameters": {}}}]
        list(provider.stream([{"role": "user", "content": "hi"}], tools=tools))
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
