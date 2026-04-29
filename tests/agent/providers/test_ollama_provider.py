"""OllamaProvider のユニットテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.providers.ollama_provider import (
    DEFAULT_OLLAMA_MODEL,
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
