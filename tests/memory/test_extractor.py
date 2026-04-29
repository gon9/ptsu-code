"""MemoryExtractor のユニットテスト (LLM はモック)。"""

from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.memory.extractor import MemoryExtractor
from ptsu_code.memory.template import DEFAULT_TEMPLATE, REQUIRED_SECTIONS


def _make_valid_memory() -> str:
    """テスト用の有効なメモリ内容を生成する。"""
    lines = []
    for section in REQUIRED_SECTIONS:
        lines.append(section)
        lines.append("_placeholder description_")
        lines.append("some content here")
        lines.append("")
    return "\n".join(lines)


class TestMemoryExtractor:
    """MemoryExtractor のテスト。"""

    @pytest.fixture()
    def mock_provider(self) -> MagicMock:
        """モック LLM プロバイダー。"""
        provider = MagicMock()
        valid_memory = _make_valid_memory()
        provider.chat.return_value = LLMResponse(content=valid_memory)
        return provider

    @pytest.fixture()
    def extractor(self, mock_provider) -> MemoryExtractor:
        """テスト用エクストラクター。"""
        return MemoryExtractor(provider=mock_provider)

    def test_extract_calls_provider_chat(self, extractor, mock_provider) -> None:
        """extract が provider.chat を呼び出すこと。"""
        conversation = [{"user": "hello", "assistant": "world"}]
        extractor.extract(conversation, DEFAULT_TEMPLATE)
        mock_provider.chat.assert_called_once()

    def test_extract_uses_temperature_zero(self, extractor, mock_provider) -> None:
        """extract が temperature=0.0 で LLM を呼び出すこと。"""
        conversation = [{"user": "hi", "assistant": "there"}]
        extractor.extract(conversation, DEFAULT_TEMPLATE)
        _, kwargs = mock_provider.chat.call_args
        assert kwargs.get("temperature") == 0.0

    def test_extract_includes_conversation_in_messages(self, extractor, mock_provider) -> None:
        """会話内容がメッセージに含まれること。"""
        conversation = [
            {"user": "create a file", "assistant": "created test.py"},
        ]
        extractor.extract(conversation, DEFAULT_TEMPLATE)
        messages = mock_provider.chat.call_args.kwargs["messages"]
        all_content = " ".join(
            m["content"] for m in messages if isinstance(m["content"], str)
        )
        assert "create a file" in all_content
        assert "created test.py" in all_content

    def test_extract_returns_provider_response(self, extractor, mock_provider) -> None:
        """extract が provider の応答を返すこと（strip 済み）。"""
        expected = _make_valid_memory()
        mock_provider.chat.return_value = LLMResponse(content=expected)
        conversation = [{"user": "a", "assistant": "b"}]
        result = extractor.extract(conversation, DEFAULT_TEMPLATE)
        assert result == expected.strip()

    def test_extract_raises_on_empty_conversation(self, extractor) -> None:
        """空の会話で ValueError が発生すること。"""
        with pytest.raises(ValueError, match="conversation is empty"):
            extractor.extract([], DEFAULT_TEMPLATE)

    def test_extract_falls_back_on_empty_response(self, extractor, mock_provider) -> None:
        """LLM が空文字を返した場合は current_memory を返すこと。"""
        mock_provider.chat.return_value = LLMResponse(content="")
        conversation = [{"user": "a", "assistant": "b"}]
        result = extractor.extract(conversation, DEFAULT_TEMPLATE)
        assert result == DEFAULT_TEMPLATE

    def test_extract_falls_back_on_missing_sections(self, extractor, mock_provider) -> None:
        """必要なセクションが欠けている場合は current_memory を返すこと。"""
        mock_provider.chat.return_value = LLMResponse(content="# Only one section")
        conversation = [{"user": "a", "assistant": "b"}]
        result = extractor.extract(conversation, DEFAULT_TEMPLATE)
        assert result == DEFAULT_TEMPLATE

    def test_extract_falls_back_on_provider_exception(self, extractor, mock_provider) -> None:
        """LLM 呼び出しが例外を投げた場合は current_memory を返すこと。"""
        mock_provider.chat.side_effect = RuntimeError("API error")
        conversation = [{"user": "a", "assistant": "b"}]
        result = extractor.extract(conversation, "my current notes")
        assert result == "my current notes"

    def test_build_messages_structure(self, extractor) -> None:
        """_build_messages がシステム → 会話 → 抽出依頼の順になること。"""
        conversation = [
            {"user": "first", "assistant": "reply1"},
            {"user": "second", "assistant": "reply2"},
        ]
        messages = extractor._build_messages(conversation, DEFAULT_TEMPLATE)

        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "first"}
        assert messages[2] == {"role": "assistant", "content": "reply1"}
        assert messages[3] == {"role": "user", "content": "second"}
        assert messages[4] == {"role": "assistant", "content": "reply2"}
        assert messages[5]["role"] == "user"
        assert "Current session notes" in messages[5]["content"]
