"""UltraPlanAgentのテスト。"""

from unittest.mock import MagicMock, patch  # noqa: F401

import pytest

from ptsu_code.agent.sub_agents.base import AgentRole
from ptsu_code.agent.sub_agents.ultraplan import UltraPlanAgent


class TestUltraPlanAgentConfig:
    """UltraPlanAgentの設定テスト。"""

    def test_config_role(self):
        """configのroleがULTRAPLANであることを確認する。"""
        agent = UltraPlanAgent()
        assert agent.config.role == AgentRole.ULTRAPLAN

    def test_config_provider_and_tier(self):
        """providerがanthropicでmodel_tierがsmartであることを確認する。"""
        agent = UltraPlanAgent()
        cfg = agent.config
        assert cfg.provider == "anthropic"
        assert cfg.model_tier == "smart"

    def test_config_allowed_tools(self):
        """許可ツールにexit_plan_modeとwrite_planが含まれることを確認する。"""
        agent = UltraPlanAgent()
        tools = agent.config.allowed_tools
        assert "exit_plan_mode" in tools
        assert "write_plan" in tools
        assert "read_file" in tools
        assert "grep_search" in tools

    def test_config_max_turns(self):
        """max_turnsが30であることを確認する。"""
        agent = UltraPlanAgent()
        assert agent.config.max_turns == 30


class TestUltraPlanAgentRun:
    """UltraPlanAgent.run()のテスト。"""

    def _make_runtime(self, provider_name: str = "anthropic") -> MagicMock:
        """テスト用のruntime mockを生成する。"""
        runtime = MagicMock()
        runtime.provider_name = provider_name
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        runtime.session_tool_registry = mock_registry
        return runtime

    def test_run_returns_approved_plan(self, tmp_path):
        """exit_plan_mode承認後にプラン内容を返すことを確認する。"""
        from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider

        plan_content = "# My Plan\n\nDo the thing."
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)

        agent = UltraPlanAgent()
        mock_runtime = self._make_runtime()
        mock_runtime.provider = MagicMock(spec=AnthropicProvider)

        text_response = MagicMock()
        text_response.content = ""
        text_response.tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "exit_plan_mode",
                    "arguments": '{"summary": "My plan", "plan_path": "' + str(plan_file) + '"}',
                },
            }
        ]

        final_response = MagicMock()
        final_response.content = "ULTRAPLAN_COMPLETE"
        final_response.tool_calls = None

        mock_runtime.provider.chat.side_effect = [text_response, final_response]

        def fake_execute_tool_calls(session, tool_calls, req_cb, prog_cb):
            import json

            from ptsu_code.agent.runtime import Message

            for tc in tool_calls:
                name = tc["function"]["name"]
                if name == "exit_plan_mode":
                    args = json.loads(tc["function"]["arguments"])
                    tool = session.tool_registry.get("exit_plan_mode")
                    if tool:
                        tool.execute(**args)
            return [
                Message(
                    role="tool",
                    content="Plan approved",
                    tool_call_id="call_1",
                    name="exit_plan_mode",
                )
            ]

        mock_runtime.execute_tool_calls.side_effect = fake_execute_tool_calls

        with patch.object(agent, "_get_runtime", return_value=mock_runtime):
            result = agent.run(mock_runtime, "ultraplan this repo")
        assert plan_content in result

    def test_run_falls_back_to_text_response(self):
        """ツール呼び出しなしでテキスト応答が返った場合はそのまま返すことを確認する。"""
        from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider

        agent = UltraPlanAgent()
        mock_runtime = self._make_runtime()
        mock_runtime.provider = MagicMock(spec=AnthropicProvider)

        response = MagicMock()
        response.content = "Here is my analysis (no tools needed)."
        response.tool_calls = None
        mock_runtime.provider.chat.return_value = response

        with patch.object(agent, "_get_runtime", return_value=mock_runtime):
            result = agent.run(mock_runtime, "ultraplan simple task")
        assert "analysis" in result

    def test_run_anthropic_uses_thinking_budget(self):
        """AnthropicProviderの場合にthinking_budgetが渡されることを確認する。"""
        from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider

        agent = UltraPlanAgent()
        mock_runtime = self._make_runtime(provider_name="anthropic")

        mock_provider = MagicMock(spec=AnthropicProvider)
        response = MagicMock()
        response.content = "done"
        response.tool_calls = None
        mock_provider.chat.return_value = response
        mock_runtime.provider = mock_provider

        with patch.object(agent, "_get_runtime", return_value=mock_runtime):
            agent.run(mock_runtime, "ultraplan test")

        call_kwargs = mock_provider.chat.call_args
        assert call_kwargs is not None
        assert "thinking_budget" in call_kwargs.kwargs
        assert call_kwargs.kwargs["thinking_budget"] == 10_000

    def test_run_non_anthropic_provider_no_thinking_budget(self):
        """anthropic以外のprovider_nameの場合にthinking_budgetが渡されないことを確認する。"""
        from ptsu_code.agent.providers.openai_provider import OpenAIProvider

        agent = UltraPlanAgent()
        mock_runtime = self._make_runtime(provider_name="openai")
        mock_runtime.provider = MagicMock(spec=OpenAIProvider)

        response = MagicMock()
        response.content = "done"
        response.tool_calls = None
        mock_runtime.provider.chat.return_value = response

        with patch.object(agent, "_get_runtime", return_value=mock_runtime):
            agent.run(mock_runtime, "ultraplan test")

        call_kwargs = mock_runtime.provider.chat.call_args
        assert call_kwargs is not None
        assert "thinking_budget" not in call_kwargs.kwargs


class TestScaleThinkingBudget:
    """_scale_thinking_budget のテスト。"""

    def setup_method(self):
        self.agent = UltraPlanAgent()

    def test_none_base_budget_returns_none(self):
        """base_budget が None なら常に None を返す。"""
        assert self.agent._scale_thinking_budget(None, 0, 30) is None
        assert self.agent._scale_thinking_budget(None, 15, 30) is None
        assert self.agent._scale_thinking_budget(None, 29, 30) is None

    def test_zero_max_turns_returns_base(self):
        """max_turns が 0 なら base_budget をそのまま返す（ZeroDivision 防止）。"""
        assert self.agent._scale_thinking_budget(10_000, 0, 0) == 10_000

    def test_early_turns_full_budget(self):
        """前半ターン (ratio < 0.33) はフル予算を返す。"""
        # turn=0, max=30 → ratio=0.0
        assert self.agent._scale_thinking_budget(10_000, 0, 30) == 10_000
        # turn=9, max=30 → ratio=0.3
        assert self.agent._scale_thinking_budget(10_000, 9, 30) == 10_000

    def test_middle_turns_half_budget(self):
        """中間ターン (0.33 <= ratio < 0.67) は半分予算を返す。"""
        # turn=10, max=30 → ratio=0.333...
        result = self.agent._scale_thinking_budget(10_000, 10, 30)
        assert result == 5_000
        # turn=19, max=30 → ratio=0.633...
        result = self.agent._scale_thinking_budget(10_000, 19, 30)
        assert result == 5_000

    def test_half_budget_minimum_is_1024(self):
        """半分予算が 1024 未満にならないこと（最小値保証）。"""
        result = self.agent._scale_thinking_budget(1024, 10, 30)
        assert result == 1024
        result = self.agent._scale_thinking_budget(512, 10, 30)
        assert result == 1024

    def test_late_turns_no_budget(self):
        """後半ターン (ratio >= 0.67) は None を返す。"""
        # turn=21, max=30 → ratio=0.70 >= 0.67
        assert self.agent._scale_thinking_budget(10_000, 21, 30) is None
        # turn=29, max=30 → ratio=0.966...
        assert self.agent._scale_thinking_budget(10_000, 29, 30) is None


class TestRateLimitRetry:
    """_run_turn_with_thinking の 429 リトライテスト。"""

    def _make_runtime(self) -> MagicMock:
        from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider

        runtime = MagicMock()
        runtime.provider_name = "anthropic"
        runtime.provider = MagicMock(spec=AnthropicProvider)
        return runtime

    def _make_session(self) -> MagicMock:
        session = MagicMock()
        session.get_messages.return_value = [{"role": "user", "content": "hi"}]
        session.tool_registry.__len__ = MagicMock(return_value=0)
        session.model = "claude-sonnet"
        session.temperature = None
        return session

    def test_retries_on_429_and_succeeds(self):
        """429 エラー後にリトライして成功することを確認する。"""

        agent = UltraPlanAgent()
        runtime = self._make_runtime()
        session = self._make_session()

        success_response = MagicMock()
        success_response.content = "ok"
        success_response.tool_calls = None

        runtime.provider.chat.side_effect = [
            Exception("Error code: 429 - rate_limit_error"),
            success_response,
        ]

        with patch("time.sleep") as mock_sleep:
            result = agent._run_turn_with_thinking(runtime, session, None)

        assert result.content == "ok"
        mock_sleep.assert_called_once_with(15)

    def test_retries_exponential_backoff(self):
        """リトライのたびに待機時間が指数的に増加することを確認する。"""
        from ptsu_code.agent.runtime import RuntimeError as PtsuRuntimeError

        agent = UltraPlanAgent()
        runtime = self._make_runtime()
        session = self._make_session()

        runtime.provider.chat.side_effect = Exception("429 rate_limit_error")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(PtsuRuntimeError):
                agent._run_turn_with_thinking(runtime, session, None)

        wait_times = [call.args[0] for call in mock_sleep.call_args_list]
        assert wait_times == [15, 30, 60, 120]

    def test_non_rate_limit_error_raises_immediately(self):
        """429 以外のエラーはリトライせずに即座に RuntimeError を送出する。"""
        from ptsu_code.agent.runtime import RuntimeError as PtsuRuntimeError

        agent = UltraPlanAgent()
        runtime = self._make_runtime()
        session = self._make_session()

        runtime.provider.chat.side_effect = Exception("500 Internal Server Error")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(PtsuRuntimeError):
                agent._run_turn_with_thinking(runtime, session, None)

        mock_sleep.assert_not_called()
        assert runtime.provider.chat.call_count == 1
