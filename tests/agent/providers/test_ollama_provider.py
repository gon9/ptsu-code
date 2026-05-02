"""OllamaProvider のユニットテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.providers.ollama_provider import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TEMPERATURE,
    OllamaProvider,
)
from ptsu_code.agent.providers.openai_provider import OpenAIProvider


@pytest.fixture()
def mock_openai_client():
    """OpenAI クライアントのモック。"""
    with patch("ptsu_code.agent.providers.openai_provider.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client, mock_cls


@pytest.fixture()
def provider(mock_openai_client) -> OllamaProvider:
    """テスト用 OllamaProvider。"""
    return OllamaProvider()


def _make_chat_response(content: str, finish_reason: str = "stop") -> MagicMock:
    """chat completion レスポンスのモックを生成する。"""
    message = MagicMock()
    message.content = content
    message.tool_calls = None

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]
    return response


class TestOllamaProviderInit:
    """OllamaProvider 初期化のテスト。"""

    def test_is_subclass_of_openai_provider(self, mock_openai_client) -> None:
        """OpenAIProvider のサブクラスであること。"""
        p = OllamaProvider()
        assert isinstance(p, OpenAIProvider)

    def test_default_model(self, mock_openai_client) -> None:
        """デフォルトモデルが DEFAULT_OLLAMA_MODEL であること。"""
        p = OllamaProvider()
        assert p.default_model == DEFAULT_OLLAMA_MODEL

    def test_custom_model(self, mock_openai_client) -> None:
        """カスタムモデルを指定できること。"""
        p = OllamaProvider(default_model="mistral")
        assert p.default_model == "mistral"

    def test_passes_base_url_to_openai_client(self, mock_openai_client) -> None:
        """base_url が OpenAI クライアントに渡されること。"""
        _, mock_cls = mock_openai_client
        OllamaProvider(base_url="http://localhost:11434/v1")
        mock_cls.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
        )

    def test_custom_base_url(self, mock_openai_client) -> None:
        """カスタム base_url を指定できること。"""
        _, mock_cls = mock_openai_client
        OllamaProvider(base_url="http://remote-host:11434/v1")
        mock_cls.assert_called_once_with(
            api_key="ollama",
            base_url="http://remote-host:11434/v1",
        )

    def test_uses_ollama_as_api_key(self, mock_openai_client) -> None:
        """api_key が 'ollama' であること（API キー不要）。"""
        _, mock_cls = mock_openai_client
        OllamaProvider()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["api_key"] == "ollama"


class TestOllamaProviderChat:
    """OllamaProvider chat メソッドのテスト。"""

    def test_chat_returns_llm_response(self, provider, mock_openai_client) -> None:
        """chat が LLMResponse を返すこと。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("hello")
        result = provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert isinstance(result, LLMResponse)
        assert result.content == "hello"

    def test_chat_uses_default_model(self, provider, mock_openai_client) -> None:
        """chat がデフォルトモデルを使用すること。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat(messages=[{"role": "user", "content": "hi"}])
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == DEFAULT_OLLAMA_MODEL

    def test_chat_with_custom_model(self, provider, mock_openai_client) -> None:
        """chat にモデル指定ができること。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat(messages=[{"role": "user", "content": "hi"}], model="mistral")
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "mistral"

    def test_chat_uses_default_temperature(self, provider, mock_openai_client) -> None:
        """temperature 未指定時は DEFAULT_OLLAMA_TEMPERATURE が使われること。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat(messages=[{"role": "user", "content": "hi"}])
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == DEFAULT_OLLAMA_TEMPERATURE

    def test_chat_uses_explicit_temperature(self, provider, mock_openai_client) -> None:
        """temperature を明示的に指定するとその値が使われること。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("ok")
        provider.chat(messages=[{"role": "user", "content": "hi"}], temperature=0.7)
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7


class TestNormalizeTools:
    """_normalize_tools のテスト。"""

    def test_none_returns_none(self, mock_openai_client) -> None:
        """None を渡すと None が返ること。"""
        assert OllamaProvider._normalize_tools(None) is None

    def test_empty_list_returns_empty(self, mock_openai_client) -> None:
        """空リストを渡すと空リストが返ること。"""
        assert OllamaProvider._normalize_tools([]) == []

    def test_adds_additional_properties_false(self, mock_openai_client) -> None:
        """additionalProperties:false が付与されること。"""
        tools = [{"type": "function", "function": {"name": "f", "parameters": {
            "type": "object", "properties": {"x": {"type": "string"}},
        }}}]
        result = OllamaProvider._normalize_tools(tools)
        assert result[0]["function"]["parameters"]["additionalProperties"] is False

    def test_adds_required_when_missing(self, mock_openai_client) -> None:
        """required が存在しない場合に全プロパティ名が追加されること。"""
        tools = [{"type": "function", "function": {"name": "f", "parameters": {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        }}}]
        result = OllamaProvider._normalize_tools(tools)
        assert set(result[0]["function"]["parameters"]["required"]) == {"a", "b"}

    def test_does_not_overwrite_existing_required(self, mock_openai_client) -> None:
        """既存の required は上書きされないこと。"""
        tools = [{"type": "function", "function": {"name": "f", "parameters": {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
            "required": ["a"],
        }}}]
        result = OllamaProvider._normalize_tools(tools)
        assert result[0]["function"]["parameters"]["required"] == ["a"]

    def test_does_not_mutate_original(self, mock_openai_client) -> None:
        """元のツールリストを変更しないこと（deepcopy）。"""
        tools = [{"type": "function", "function": {"name": "f", "parameters": {
            "type": "object", "properties": {"x": {"type": "string"}},
        }}}]
        original_params = dict(tools[0]["function"]["parameters"])
        OllamaProvider._normalize_tools(tools)
        assert "additionalProperties" not in original_params

    def test_non_function_tool_is_passed_through(self, mock_openai_client) -> None:
        """type が function 以外のツールはそのまま通過すること。"""
        tools = [{"type": "retrieval", "retrieval": {}}]
        result = OllamaProvider._normalize_tools(tools)
        assert result == tools


class TestOllamaProviderStream:
    """OllamaProvider stream のテスト。"""

    def test_stream_with_tools_falls_back_to_chat(self, provider, mock_openai_client) -> None:
        """ツールあり時はストリーミングせず chat() にフォールバックすること。"""
        client, _ = mock_openai_client
        client.chat.completions.create.return_value = _make_chat_response("result")
        tools = [{"type": "function", "function": {"name": "f", "parameters": {
            "type": "object", "properties": {},
        }}}]
        chunks = list(provider.stream(
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        ))
        assert len(chunks) == 1
        assert chunks[0].is_final is True
        assert chunks[0].final_response.content == "result"

    def test_stream_without_tools_uses_streaming(self, provider, mock_openai_client) -> None:
        """ツールなし時はストリーミングが使われること（stream=True が渡る）。"""
        client, _ = mock_openai_client

        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "hello"
        mock_chunk.choices[0].delta.tool_calls = None
        mock_chunk.choices[0].finish_reason = "stop"
        client.chat.completions.create.return_value = iter([mock_chunk])

        list(provider.stream(messages=[{"role": "user", "content": "hi"}]))
        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("stream") is True
