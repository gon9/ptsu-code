"""Intent分類器のテスト。"""

from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.intent import Intent, IntentClassifier, IntentResult
from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.sub_agents.base import AgentRole


def _make_provider(json_content: str) -> MagicMock:
    """指定のJSONを返すMockプロバイダーを生成する。"""
    provider = MagicMock()
    provider.chat.return_value = LLMResponse(content=json_content)
    return provider


class TestIntent:
    """IntentEnumのテスト。"""

    def test_intent_values(self):
        """全Intent値が正しいことを確認する。"""
        assert Intent.SEARCH.value == "search"
        assert Intent.CODE.value == "code"
        assert Intent.EXECUTE.value == "execute"
        assert Intent.QUESTION.value == "question"
        assert Intent.MULTI.value == "multi"

    def test_all_intents_exist(self):
        """全Intentが定義されていることを確認する。"""
        values = {i.value for i in Intent}
        assert values == {"search", "code", "execute", "question", "multi"}


class TestIntentResult:
    """IntentResultのテスト。"""

    def test_default_fields(self):
        """デフォルトフィールドが正しいことを確認する。"""
        result = IntentResult(primary=Intent.QUESTION, confidence=0.9)
        assert result.sub_intents == []
        assert result.reasoning == ""
        assert result.suggested_agent == AgentRole.GENERAL

    def test_custom_fields(self):
        """カスタムフィールドが正しく設定されることを確認する。"""
        result = IntentResult(
            primary=Intent.SEARCH,
            confidence=0.85,
            sub_intents=[Intent.CODE],
            reasoning="User wants to find and edit code",
            suggested_agent=AgentRole.SEARCHER,
        )
        assert result.primary == Intent.SEARCH
        assert result.confidence == 0.85
        assert result.sub_intents == [Intent.CODE]
        assert result.suggested_agent == AgentRole.SEARCHER


class TestIntentClassifier:
    """IntentClassifierのテスト。"""

    @pytest.mark.parametrize(
        "json_response, expected_intent, expected_agent",
        [
            (
                '{"primary": "SEARCH", "confidence": 0.9, "sub_intents": [], "reasoning": "search", "suggested_agent": "searcher"}',
                Intent.SEARCH,
                AgentRole.SEARCHER,
            ),
            (
                '{"primary": "CODE", "confidence": 0.8, "sub_intents": [], "reasoning": "code", "suggested_agent": "coder"}',
                Intent.CODE,
                AgentRole.CODER,
            ),
            (
                '{"primary": "EXECUTE", "confidence": 0.7, "sub_intents": [], "reasoning": "exec", "suggested_agent": "executor"}',
                Intent.EXECUTE,
                AgentRole.EXECUTOR,
            ),
            (
                '{"primary": "QUESTION", "confidence": 0.95, "sub_intents": [], "reasoning": "q", "suggested_agent": "general"}',
                Intent.QUESTION,
                AgentRole.GENERAL,
            ),
            (
                '{"primary": "MULTI", "confidence": 0.6, "sub_intents": ["SEARCH", "CODE"], "reasoning": "multi", "suggested_agent": "general"}',
                Intent.MULTI,
                AgentRole.GENERAL,
            ),
        ],
    )
    def test_classify_returns_correct_intent(self, json_response, expected_intent, expected_agent):
        """各Intentタイプが正しく分類されることを確認する。"""
        classifier = IntentClassifier(_make_provider(json_response))
        result = classifier.classify("some message")
        assert result.primary == expected_intent
        assert result.suggested_agent == expected_agent

    def test_classify_empty_message_returns_question(self):
        """空メッセージはQUESTIONを返すことを確認する。"""
        classifier = IntentClassifier(MagicMock())
        result = classifier.classify("")
        assert result.primary == Intent.QUESTION
        assert result.confidence == 1.0

    def test_classify_whitespace_only_returns_question(self):
        """空白のみのメッセージはQUESTIONを返すことを確認する。"""
        classifier = IntentClassifier(MagicMock())
        result = classifier.classify("   ")
        assert result.primary == Intent.QUESTION

    def test_classify_with_sub_intents(self):
        """sub_intentsが正しくパースされることを確認する。"""
        json_response = '{"primary": "MULTI", "confidence": 0.75, "sub_intents": ["SEARCH", "CODE"], "reasoning": "multi", "suggested_agent": "general"}'
        classifier = IntentClassifier(_make_provider(json_response))
        result = classifier.classify("find and fix the bug")
        assert Intent.SEARCH in result.sub_intents
        assert Intent.CODE in result.sub_intents

    def test_classify_confidence_clamped(self):
        """confidenceが0.0〜1.0にクランプされることを確認する。"""
        json_response = '{"primary": "CODE", "confidence": 2.5, "sub_intents": [], "reasoning": "x", "suggested_agent": "coder"}'
        classifier = IntentClassifier(_make_provider(json_response))
        result = classifier.classify("write code")
        assert result.confidence == 1.0

    def test_classify_provider_error_fallback(self):
        """プロバイダーエラー時にフォールバックすることを確認する。"""
        provider = MagicMock()
        provider.chat.side_effect = Exception("API error")
        classifier = IntentClassifier(provider)
        result = classifier.classify("run the tests")
        assert isinstance(result, IntentResult)
        assert isinstance(result.primary, Intent)

    def test_classify_invalid_json_fallback(self):
        """無効なJSONレスポンス時にフォールバックすることを確認する。"""
        classifier = IntentClassifier(_make_provider("not valid json at all"))
        result = classifier.classify("something")
        assert result.primary == Intent.QUESTION
        assert result.confidence == 0.3

    def test_classify_with_conversation_history(self):
        """会話履歴を渡せることを確認する。"""
        json_response = '{"primary": "SEARCH", "confidence": 0.8, "sub_intents": [], "reasoning": "search", "suggested_agent": "searcher"}'
        provider = _make_provider(json_response)
        classifier = IntentClassifier(provider)
        history = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        result = classifier.classify("find the config file", conversation_history=history)
        assert result.primary == Intent.SEARCH
        call_args = provider.chat.call_args
        messages_sent = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        assert len(messages_sent) == 3

    def test_fallback_keyword_search(self):
        """検索キーワードでフォールバック分類されることを確認する。"""
        provider = MagicMock()
        provider.chat.side_effect = Exception("error")
        classifier = IntentClassifier(provider)
        result = classifier.classify("find where the login is")
        assert result.primary == Intent.SEARCH
        assert result.suggested_agent == AgentRole.SEARCHER

    def test_fallback_keyword_execute(self):
        """実行キーワードでフォールバック分類されることを確認する。"""
        provider = MagicMock()
        provider.chat.side_effect = Exception("error")
        classifier = IntentClassifier(provider)
        result = classifier.classify("run the tests")
        assert result.primary == Intent.EXECUTE
        assert result.suggested_agent == AgentRole.EXECUTOR

    def test_fallback_keyword_code(self):
        """コードキーワードでフォールバック分類されることを確認する。"""
        provider = MagicMock()
        provider.chat.side_effect = Exception("error")
        classifier = IntentClassifier(provider)
        result = classifier.classify("write a new function")
        assert result.primary == Intent.CODE
        assert result.suggested_agent == AgentRole.CODER

    def test_classify_json_embedded_in_text(self):
        """テキストに埋め込まれたJSONを正しくパースすることを確認する。"""
        json_response = 'Here is the classification: {"primary": "CODE", "confidence": 0.9, "sub_intents": [], "reasoning": "coding task", "suggested_agent": "coder"} Done.'
        classifier = IntentClassifier(_make_provider(json_response))
        result = classifier.classify("add a new feature")
        assert result.primary == Intent.CODE
