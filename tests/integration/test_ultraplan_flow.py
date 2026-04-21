"""ULTRAPLAN 統合テスト (UAT-UP-04/05/06 自動検証)。

実 API を使わずに Coordinator → UltraPlanAgent のフルフローを検証する。
UAT-UP-01〜03 (TTY + 実 LLM が必要) は手動実施。
"""

import json
from unittest.mock import MagicMock, patch

from ptsu_code.agent.coordinator import Coordinator
from ptsu_code.agent.intent import Intent, IntentClassifier, has_ultraplan_keyword
from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider
from ptsu_code.agent.providers.base import LLMResponse
from ptsu_code.agent.sub_agents.base import AgentRole
from ptsu_code.agent.sub_agents.ultraplan import UltraPlanAgent
from ptsu_code.agent.tools.plan_tools import ExitPlanModeTool, WritePlanTool


def _make_llm_response(content: str, tool_calls: list | None = None) -> LLMResponse:
    """テスト用 LLMResponse を生成する。"""
    return LLMResponse(content=content, tool_calls=tool_calls)


def _make_exit_plan_mode_call(summary: str, plan_path: str) -> dict:
    """exit_plan_mode ツール呼び出しを模倣するdict を生成する。"""
    return {
        "id": "call_exit",
        "type": "function",
        "function": {
            "name": "exit_plan_mode",
            "arguments": json.dumps({"summary": summary, "plan_path": plan_path}),
        },
    }


def _make_write_plan_call(content: str, path: str) -> dict:
    """write_plan ツール呼び出しを模倣するdict を生成する。"""
    return {
        "id": "call_write",
        "type": "function",
        "function": {
            "name": "write_plan",
            "arguments": json.dumps({"content": content, "path": path}),
        },
    }


class TestUATUP05KeywordRouting:
    """UAT-UP-05/06: キーワードルーティング自動検証。"""

    def test_up05_ultraplan_keyword_lowercase(self):
        """[UP-05変形] 小文字 ultraplan でもルーティングされる。"""
        assert has_ultraplan_keyword("ultraplan this codebase") is True

    def test_up05_ultraplan_keyword_uppercase(self):
        """[UP-05] 大文字 ULTRAPLAN でもルーティングされる。"""
        assert has_ultraplan_keyword("ULTRAPLAN this project") is True

    def test_up05_ultraplan_keyword_mixed_case(self):
        """[UP-05] 混合大文字でも検出できる。"""
        assert has_ultraplan_keyword("UltraPlan the architecture") is True

    def test_up06_no_ultraplan_keyword(self):
        """[UP-06] ultraplan を含まないメッセージは False。"""
        assert has_ultraplan_keyword("list the files in src/") is False
        assert has_ultraplan_keyword("write a plan for me") is False
        assert has_ultraplan_keyword("") is False

    def test_up05_classifier_bypasses_llm(self):
        """[UP-05] ultraplan キーワードがあれば LLM を呼ばずに ULTRAPLAN Intent を返す。"""
        mock_provider = MagicMock()
        classifier = IntentClassifier(mock_provider)

        result = classifier.classify("ULTRAPLAN the src directory")

        assert result.primary == Intent.ULTRAPLAN
        assert result.suggested_agent == AgentRole.ULTRAPLAN
        assert result.confidence == 1.0
        mock_provider.chat.assert_not_called()

    def test_up06_non_ultraplan_routes_to_general(self):
        """[UP-06] 通常メッセージは ULTRAPLAN にルーティングされない。"""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = LLMResponse(
            content='{"primary": "SEARCH", "confidence": 0.9, "sub_intents": [], "reasoning": "search", "suggested_agent": "searcher"}'
        )
        classifier = IntentClassifier(mock_provider)
        result = classifier.classify("list the files in src/")
        assert result.primary != Intent.ULTRAPLAN


class TestUATUP04PlanFile:
    """UAT-UP-04: write_plan → ファイル生成確認。"""

    def test_write_plan_creates_file(self, tmp_path):
        """[UP-04] WritePlanTool がプランファイルを生成する。"""
        plan_file = tmp_path / "plan.md"
        tool = WritePlanTool()
        content = "# Implementation Plan\n\nStep 1: Do something\nStep 2: Do more"

        result = tool.execute(content=content, path=str(plan_file))

        assert result.success is True
        assert plan_file.exists()
        assert plan_file.read_text() == content

    def test_exit_plan_mode_reads_plan_file(self, tmp_path):
        """[UP-04] ExitPlanModeTool が承認時にファイル内容を取得する。"""
        plan_file = tmp_path / "plan.md"
        plan_content = "# My Plan\n\nDo the thing."
        plan_file.write_text(plan_content)

        tool = ExitPlanModeTool()
        result = tool.execute(summary="Do the thing", plan_path=str(plan_file))

        assert result.success is True
        assert tool.plan_approved is True
        assert tool.approved_plan == plan_content


class TestUATUP01CoordinatorDispatch:
    """UAT-UP-01 (自動化可能部分): Coordinator → UltraPlanAgent ディスパッチ確認。"""

    def test_coordinator_dispatches_to_ultraplan_agent(self):
        """[UP-01] ultraplan キーワード入力で UltraPlanAgent が呼ばれる。"""
        mock_runtime = MagicMock()
        mock_runtime.provider_name = "anthropic"
        mock_runtime.provider = MagicMock(spec=AnthropicProvider)
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        mock_runtime.session_tool_registry = mock_registry

        mock_provider_for_classifier = MagicMock()
        classifier = IntentClassifier(mock_provider_for_classifier)

        mock_agent = MagicMock(spec=UltraPlanAgent)
        mock_agent.config.role = AgentRole.ULTRAPLAN
        mock_agent.config.name = "UltraPlan"
        mock_agent.run.return_value = "# My Plan\n\nHere is the approved plan."

        agents = {AgentRole.ULTRAPLAN: mock_agent}
        coordinator = Coordinator(
            runtime=mock_runtime, classifier=classifier, agents=agents
        )

        dispatched_roles = []

        def on_dispatch(role, name):
            dispatched_roles.append(role)

        result = coordinator.process(
            "ultraplan the codebase",
            on_dispatch=on_dispatch,
        )

        assert AgentRole.ULTRAPLAN in dispatched_roles
        mock_agent.run.assert_called_once()
        assert "My Plan" in result

    def test_coordinator_dispatches_ultraplan_case_insensitive(self):
        """[UP-05] 大文字 ULTRAPLAN でも UltraPlanAgent がディスパッチされる。"""
        mock_runtime = MagicMock()
        mock_provider_for_classifier = MagicMock()
        classifier = IntentClassifier(mock_provider_for_classifier)

        mock_agent = MagicMock(spec=UltraPlanAgent)
        mock_agent.config.role = AgentRole.ULTRAPLAN
        mock_agent.config.name = "UltraPlan"
        mock_agent.run.return_value = "Plan content"

        agents = {AgentRole.ULTRAPLAN: mock_agent}
        coordinator = Coordinator(
            runtime=mock_runtime, classifier=classifier, agents=agents
        )

        dispatched_roles = []
        coordinator.process(
            "ULTRAPLAN the architecture",
            on_dispatch=lambda r, n: dispatched_roles.append(r),
        )

        assert AgentRole.ULTRAPLAN in dispatched_roles


class TestUATUP02UP03ApprovalFlow:
    """UAT-UP-02/03 (自動化): 承認・却下フローの論理確認。"""

    def _make_runtime(self, provider: AnthropicProvider) -> MagicMock:
        runtime = MagicMock()
        runtime.provider_name = "anthropic"
        runtime.provider = provider
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        runtime.session_tool_registry = mock_registry
        return runtime

    def test_up02_plan_approved_returns_plan_content(self, tmp_path):
        """[UP-02] exit_plan_mode が承認されるとプラン内容が返る。"""
        plan_content = "# Approved Plan\n\nImplement the feature."
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        mock_provider = MagicMock(spec=AnthropicProvider)
        runtime = self._make_runtime(mock_provider)

        turn1 = _make_llm_response(
            content="",
            tool_calls=[_make_exit_plan_mode_call("The plan", str(plan_file))],
        )
        mock_provider.chat.return_value = turn1

        agent = UltraPlanAgent()

        def auto_approve(tool_name: str, args: dict) -> str:
            if tool_name == "exit_plan_mode":
                return "y"
            return "y"

        def fake_execute(session, tool_calls, req_cb, prog_cb):
            from ptsu_code.agent.runtime import Message

            results = []
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                tool = session.tool_registry.get(name)
                if tool and req_cb:
                    decision = req_cb(name, args)
                    if decision in ("y", "a"):
                        tool.execute(**args)
                results.append(
                    Message(role="tool", content="ok", tool_call_id=tc["id"], name=name)
                )
            return results

        runtime.execute_tool_calls.side_effect = fake_execute

        with patch.object(agent, "_get_runtime", return_value=runtime):
            result = agent.run(
                runtime,
                "ultraplan the codebase",
                request_approval_callback=auto_approve,
            )

        assert plan_content in result

    def test_up03_plan_rejected_continues_loop(self, tmp_path):
        """[UP-03] exit_plan_mode が却下されるとループが継続する。"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("Draft plan")

        mock_provider = MagicMock(spec=AnthropicProvider)
        runtime = self._make_runtime(mock_provider)

        turn1 = _make_llm_response(
            content="",
            tool_calls=[_make_exit_plan_mode_call("Draft", str(plan_file))],
        )
        turn2 = _make_llm_response(content="No more tools", tool_calls=None)
        mock_provider.chat.side_effect = [turn1, turn2]

        agent = UltraPlanAgent()
        call_count = {"n": 0}

        def reject_first_then_quit(tool_name: str, args: dict) -> str:
            if tool_name == "exit_plan_mode":
                call_count["n"] += 1
                return "n"
            return "y"

        def fake_execute(session, tool_calls, req_cb, prog_cb):
            from ptsu_code.agent.runtime import Message

            results = []
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                tool = session.tool_registry.get(name)
                if tool and req_cb:
                    decision = req_cb(name, args)
                    if decision not in ("n", "no"):
                        tool.execute(**args)
                results.append(
                    Message(role="tool", content="rejected", tool_call_id=tc["id"], name=name)
                )
            return results

        runtime.execute_tool_calls.side_effect = fake_execute

        with patch.object(agent, "_get_runtime", return_value=runtime):
            agent.run(
                runtime,
                "ultraplan the codebase",
                request_approval_callback=reject_first_then_quit,
            )

        assert call_count["n"] >= 1
        assert mock_provider.chat.call_count == 2
