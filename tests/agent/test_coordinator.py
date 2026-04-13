"""Coordinatorのテスト。"""

from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.coordinator import Coordinator, DispatchResult
from ptsu_code.agent.intent import Intent, IntentResult
from ptsu_code.agent.sub_agents.base import AgentRole


def _make_intent_result(primary: Intent, suggested_agent: AgentRole, sub_intents=None) -> IntentResult:
    """テスト用IntentResultを生成する。"""
    return IntentResult(
        primary=primary,
        confidence=0.9,
        sub_intents=sub_intents or [],
        reasoning="test",
        suggested_agent=suggested_agent,
    )


def _make_agent(name: str, role: AgentRole, return_value: str = "result") -> MagicMock:
    """テスト用Sub-agentMockを生成する。"""
    agent = MagicMock()
    agent.config.name = name
    agent.config.role = role
    agent.run.return_value = return_value
    return agent


def _make_coordinator(
    primary: Intent = Intent.SEARCH,
    suggested_agent: AgentRole = AgentRole.SEARCHER,
    sub_intents=None,
) -> tuple[Coordinator, MagicMock, dict]:
    """テスト用Coordinatorを生成する。"""
    runtime = MagicMock()

    classifier = MagicMock()
    classifier.classify.return_value = _make_intent_result(primary, suggested_agent, sub_intents)

    agents = {
        AgentRole.SEARCHER: _make_agent("Searcher", AgentRole.SEARCHER, "search result"),
        AgentRole.CODER: _make_agent("Coder", AgentRole.CODER, "code result"),
        AgentRole.EXECUTOR: _make_agent("Executor", AgentRole.EXECUTOR, "exec result"),
        AgentRole.GENERAL: _make_agent("General", AgentRole.GENERAL, "general result"),
    }

    coord = Coordinator(runtime=runtime, classifier=classifier, agents=agents)
    return coord, runtime, agents


class TestDispatchResult:
    """DispatchResultのテスト。"""

    def test_dispatch_result_fields(self):
        """DispatchResultのフィールドが正しく設定されることを確認する。"""
        intent = _make_intent_result(Intent.SEARCH, AgentRole.SEARCHER)
        result = DispatchResult(
            agent_role=AgentRole.SEARCHER,
            agent_name="Searcher",
            result="found files",
            intent=intent,
        )
        assert result.agent_role == AgentRole.SEARCHER
        assert result.agent_name == "Searcher"
        assert result.result == "found files"


class TestCoordinatorProcess:
    """Coordinator.processのテスト。"""

    @pytest.mark.parametrize("primary,suggested,expected_agent_key", [
        (Intent.SEARCH, AgentRole.SEARCHER, AgentRole.SEARCHER),
        (Intent.CODE, AgentRole.CODER, AgentRole.CODER),
        (Intent.EXECUTE, AgentRole.EXECUTOR, AgentRole.EXECUTOR),
        (Intent.QUESTION, AgentRole.GENERAL, AgentRole.GENERAL),
    ])
    def test_process_dispatches_to_correct_agent(self, primary, suggested, expected_agent_key):
        """各intentが正しいSub-agentにディスパッチされることを確認する。"""
        coord, runtime, agents = _make_coordinator(primary=primary, suggested_agent=suggested)
        coord.process("test message")
        agents[expected_agent_key].run.assert_called_once()

    def test_process_calls_classifier(self):
        """processがIntentClassifier.classifyを呼び出すことを確認する。"""
        coord, _, _ = _make_coordinator()
        coord.process("find the config")
        coord.classifier.classify.assert_called_once_with("find the config")

    def test_process_returns_agent_result(self):
        """processがSub-agentの結果を返すことを確認する。"""
        coord, _, _ = _make_coordinator(primary=Intent.SEARCH, suggested_agent=AgentRole.SEARCHER)
        result = coord.process("find something")
        assert result == "search result"

    def test_process_calls_on_dispatch_callback(self):
        """on_dispatchコールバックが呼ばれることを確認する。"""
        coord, _, _ = _make_coordinator(primary=Intent.SEARCH, suggested_agent=AgentRole.SEARCHER)
        on_dispatch = MagicMock()
        coord.process("find something", on_dispatch=on_dispatch)
        on_dispatch.assert_called_once()

    def test_process_without_on_dispatch(self):
        """on_dispatchなしでprocessが動作することを確認する。"""
        coord, _, _ = _make_coordinator()
        result = coord.process("message")
        assert result is not None

    def test_process_passes_context_to_agent(self):
        """contextがSub-agentに渡されることを確認する。"""
        coord, _, agents = _make_coordinator(primary=Intent.SEARCH, suggested_agent=AgentRole.SEARCHER)
        ctx = {"cwd": "/project"}
        coord.process("find files", context=ctx)
        agents[AgentRole.SEARCHER].run.assert_called_once_with(coord.runtime, "find files", ctx)


class TestCoordinatorMultiIntent:
    """Coordinator MULTI intent処理のテスト。"""

    def test_multi_intent_runs_multiple_agents(self):
        """MULTI intentで複数のSub-agentが実行されることを確認する。"""
        coord, _, agents = _make_coordinator(
            primary=Intent.MULTI,
            suggested_agent=AgentRole.GENERAL,
            sub_intents=[Intent.SEARCH, Intent.CODE],
        )
        coord.process("find and fix the bug")
        agents[AgentRole.SEARCHER].run.assert_called_once()
        agents[AgentRole.CODER].run.assert_called_once()

    def test_multi_intent_result_contains_all_agent_results(self):
        """MULTI intentの結果に全Sub-agentの出力が含まれることを確認する。"""
        coord, _, _ = _make_coordinator(
            primary=Intent.MULTI,
            suggested_agent=AgentRole.GENERAL,
            sub_intents=[Intent.SEARCH, Intent.CODE],
        )
        result = coord.process("find and fix the bug")
        assert "search result" in result
        assert "code result" in result

    def test_multi_intent_no_duplicate_agents(self):
        """MULTI intentで同じロールのSub-agentが重複実行されないことを確認する。"""
        coord, _, agents = _make_coordinator(
            primary=Intent.MULTI,
            suggested_agent=AgentRole.GENERAL,
            sub_intents=[Intent.SEARCH, Intent.SEARCH, Intent.CODE],
        )
        coord.process("search twice then code")
        assert agents[AgentRole.SEARCHER].run.call_count == 1

    def test_multi_intent_empty_sub_intents_uses_fallback(self):
        """sub_intentsが空のMULTI intentはフォールバックSub-agentを使うことを確認する。"""
        coord, _, agents = _make_coordinator(
            primary=Intent.MULTI,
            suggested_agent=AgentRole.GENERAL,
            sub_intents=[],
        )
        result = coord.process("multi without sub intents")
        assert result == "general result"

    def test_multi_intent_on_dispatch_called_for_each_agent(self):
        """MULTI intentでon_dispatchが各Sub-agentに対して呼ばれることを確認する。"""
        coord, _, _ = _make_coordinator(
            primary=Intent.MULTI,
            suggested_agent=AgentRole.GENERAL,
            sub_intents=[Intent.SEARCH, Intent.CODE],
        )
        on_dispatch = MagicMock()
        coord.process("find and code", on_dispatch=on_dispatch)
        assert on_dispatch.call_count == 2


class TestCoordinatorSelectAgent:
    """Coordinator._select_agentのテスト。"""

    def test_select_known_role(self):
        """既知のロールが正しく選択されることを確認する。"""
        coord, _, agents = _make_coordinator()
        agent = coord._select_agent(AgentRole.CODER)
        assert agent is agents[AgentRole.CODER]

    def test_select_unknown_role_falls_back_to_general(self):
        """未知のロールでGENERALにフォールバックすることを確認する。"""
        runtime = MagicMock()
        classifier = MagicMock()
        general_agent = _make_agent("General", AgentRole.GENERAL)
        agents = {AgentRole.GENERAL: general_agent}
        coord = Coordinator(runtime=runtime, classifier=classifier, agents=agents)
        result = coord._select_agent(AgentRole.SEARCHER)
        assert result is general_agent

    def test_select_no_agents_returns_first(self):
        """agentsが1つだけの場合は最初のSub-agentを返すことを確認する。"""
        runtime = MagicMock()
        classifier = MagicMock()
        only_agent = _make_agent("Only", AgentRole.CODER)
        coord = Coordinator(runtime=runtime, classifier=classifier, agents={AgentRole.CODER: only_agent})
        result = coord._select_agent(AgentRole.SEARCHER)
        assert result is only_agent
