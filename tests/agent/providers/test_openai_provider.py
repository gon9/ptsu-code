"""OpenAIProviderのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.providers.openai_provider import OpenAIProvider


@pytest.fixture
def mock_openai_client():
    """OpenAIクライアントのモック。"""
    with patch("ptsu_code.agent.providers.openai_provider.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def provider(mock_openai_client):
    """テスト用OpenAIProvider。"""
    return OpenAIProvider(api_key="test-key")


def _make_chat_response(content: str, tool_calls=None, finish_reason: str = "stop"):
    """OpenAI chat completion レスポンスのモックを生成する。"""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_stream_chunk(content_delta=None, tool_call_deltas=None, finish_reason=None):
    """OpenAI streaming chunk のモックを生成する。"""
    delta = MagicMock()
    delta.content = content_delta
    delta.tool_calls = tool_call_deltas

    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = finish_reason

    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


class TestOpenAIProviderInit:
    """OpenAIProvider初期化テスト。"""

    def test_init_sets_default_model(self, mock_openai_client):
        """デフォルトモデルが設定されることを確認する。"""
        p = OpenAIProvider(api_key="key")
        assert p.default_model == "gpt-4o-mini"

    def test_init_custom_model(self, mock_openai_client):
        """カスタムモデルが設定されることを確認する。"""
        p = OpenAIProvider(api_key="key", default_model="gpt-4o")
        assert p.default_model == "gpt-4o"


class TestOpenAIProviderChat:
    """OpenAIProvider.chatのテスト。"""

    def test_chat_returns_llm_response(self, provider, mock_openai_client):
        """chatがLLMResponseを返すことを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response("Hello!")
        result = provider.chat([{"role": "user", "content": "Hi"}])
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello!"

    def test_chat_without_tools(self, provider, mock_openai_client):
        """ツールなしのchatが動作することを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response("No tools")
        result = provider.chat([{"role": "user", "content": "msg"}], tools=None)
        assert result.content == "No tools"
        assert result.tool_calls is None

    def test_chat_finish_reason(self, provider, mock_openai_client):
        """finish_reasonが正しく返されることを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response(
            "done", finish_reason="stop"
        )
        result = provider.chat([{"role": "user", "content": "msg"}])
        assert result.finish_reason == "stop"

    def test_chat_with_tool_calls(self, provider, mock_openai_client):
        """ツール呼び出しがあるchatレスポンスが正しく変換されることを確認する。"""
        tc = MagicMock()
        tc.model_dump.return_value = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "x.py"}'},
        }
        mock_openai_client.chat.completions.create.return_value = _make_chat_response(
            "", tool_calls=[tc], finish_reason="tool_calls"
        )
        result = provider.chat([{"role": "user", "content": "read x.py"}])
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1

    def test_chat_uses_custom_model(self, provider, mock_openai_client):
        """カスタムモデルが渡されることを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat([{"role": "user", "content": "msg"}], model="gpt-4o")
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_chat_uses_default_model_when_none(self, provider, mock_openai_client):
        """モデルがNoneのときデフォルトモデルが使われることを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat([{"role": "user", "content": "msg"}], model=None)
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_chat_empty_content_returns_empty_string(self, provider, mock_openai_client):
        """contentがNoneのとき空文字列が返されることを確認する。"""
        mock_openai_client.chat.completions.create.return_value = _make_chat_response(None)
        result = provider.chat([{"role": "user", "content": "msg"}])
        assert result.content == ""


class TestOpenAIProviderStream:
    """OpenAIProvider.streamのテスト。"""

    def test_stream_yields_content_chunks(self, provider, mock_openai_client):
        """コンテンツチャンクが正しくyieldされることを確認する。"""
        chunks = [
            _make_stream_chunk(content_delta="Hello"),
            _make_stream_chunk(content_delta=" World"),
            _make_stream_chunk(finish_reason="stop"),
        ]
        mock_openai_client.chat.completions.create.return_value = iter(chunks)

        result_chunks = list(provider.stream([{"role": "user", "content": "hi"}]))

        content_chunks = [c for c in result_chunks if c.content_delta]
        assert len(content_chunks) == 2
        assert content_chunks[0].content_delta == "Hello"
        assert content_chunks[1].content_delta == " World"

    def test_stream_yields_final_chunk(self, provider, mock_openai_client):
        """最終チャンクが正しくyieldされることを確認する。"""
        chunks = [
            _make_stream_chunk(content_delta="Hi"),
            _make_stream_chunk(finish_reason="stop"),
        ]
        mock_openai_client.chat.completions.create.return_value = iter(chunks)

        result_chunks = list(provider.stream([{"role": "user", "content": "hi"}]))

        final_chunks = [c for c in result_chunks if c.is_final]
        assert len(final_chunks) == 1
        assert final_chunks[0].final_response is not None
        assert final_chunks[0].final_response.content == "Hi"

    def test_stream_with_tools(self, provider, mock_openai_client):
        """ツール付きのストリームが動作することを確認する。"""
        chunks = [_make_stream_chunk(finish_reason="stop")]
        mock_openai_client.chat.completions.create.return_value = iter(chunks)
        tools = [{"type": "function", "function": {"name": "test", "description": "test", "parameters": {}}}]

        result_chunks = list(provider.stream([{"role": "user", "content": "hi"}], tools=tools))
        assert len(result_chunks) >= 1

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert "tools" in call_kwargs

    def test_stream_without_tools_no_tools_kwarg(self, provider, mock_openai_client):
        """ツールなしのストリームでtools kwargが渡されないことを確認する。"""
        chunks = [_make_stream_chunk(finish_reason="stop")]
        mock_openai_client.chat.completions.create.return_value = iter(chunks)

        list(provider.stream([{"role": "user", "content": "hi"}], tools=None))

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert "tools" not in call_kwargs

    def test_stream_assembles_tool_calls(self, provider, mock_openai_client):
        """ツール呼び出しのデルタが正しくアセンブルされることを確認する。"""
        tc_delta_1 = MagicMock()
        tc_delta_1.index = 0
        tc_delta_1.id = "call_abc"
        tc_delta_1.function = MagicMock()
        tc_delta_1.function.name = "read_file"
        tc_delta_1.function.arguments = '{"path":'

        tc_delta_2 = MagicMock()
        tc_delta_2.index = 0
        tc_delta_2.id = None
        tc_delta_2.function = MagicMock()
        tc_delta_2.function.name = None
        tc_delta_2.function.arguments = '"x.py"}'

        chunks = [
            _make_stream_chunk(tool_call_deltas=[tc_delta_1]),
            _make_stream_chunk(tool_call_deltas=[tc_delta_2]),
            _make_stream_chunk(finish_reason="tool_calls"),
        ]
        mock_openai_client.chat.completions.create.return_value = iter(chunks)

        result_chunks = list(provider.stream([{"role": "user", "content": "read"}]))

        final = next(c for c in result_chunks if c.is_final)
        assert final.final_response.tool_calls is not None
        tc = final.final_response.tool_calls[0]
        assert tc["function"]["name"] == "read_file"
        assert '"x.py"}' in tc["function"]["arguments"]
