"""ExecutorAgentのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgentConfig
from ptsu_code.agent.sub_agents.executor import ExecutorAgent


class TestExecutorAgentConfig:
    """ExecutorAgentの設定テスト。"""

    def test_config_role(self):
        """ロールがEXECUTORであることを確認する。"""
        agent = ExecutorAgent()
        assert agent.config.role == AgentRole.EXECUTOR

    def test_config_name(self):
        """名前が正しいことを確認する。"""
        agent = ExecutorAgent()
        assert agent.config.name == "Executor"

    def test_config_allowed_tools_includes_execute(self):
        """allowed_toolsにexecute_commandが含まれることを確認する。"""
        agent = ExecutorAgent()
        assert "execute_command" in agent.config.allowed_tools

    def test_config_allowed_tools_includes_read(self):
        """allowed_toolsにread_fileが含まれることを確認する。"""
        agent = ExecutorAgent()
        assert "read_file" in agent.config.allowed_tools

    def test_config_no_write_file(self):
        """write_fileが許可されていないことを確認する。"""
        agent = ExecutorAgent()
        assert "write_file" not in agent.config.allowed_tools

    def test_config_no_grep_search(self):
        """grep_searchが許可されていないことを確認する。"""
        agent = ExecutorAgent()
        assert "grep_search" not in agent.config.allowed_tools

    def test_config_temperature(self):
        """temperatureがNone（モデルデフォルト使用）であることを確認する。"""
        agent = ExecutorAgent()
        assert agent.config.temperature is None

    def test_config_max_turns(self):
        """max_turnsが5であることを確認する。"""
        agent = ExecutorAgent()
        assert agent.config.max_turns == 5

    def test_config_returns_subagentconfig_type(self):
        """configがSubAgentConfigを返すことを確認する。"""
        agent = ExecutorAgent()
        assert isinstance(agent.config, SubAgentConfig)

    def test_system_prompt_mentions_executor(self):
        """システムプロンプトにExecutor Agentの説明が含まれることを確認する。"""
        agent = ExecutorAgent()
        assert "Executor Agent" in agent.config.system_prompt

    def test_system_prompt_warns_no_source_modification(self):
        """システムプロンプトにソースコード変更禁止の指示が含まれることを確認する。"""
        agent = ExecutorAgent()
        prompt = agent.config.system_prompt
        assert "DO NOT modify" in prompt


class TestExecutorAgentRun:
    """ExecutorAgent.runのテスト。"""

    def test_run_calls_runtime_run_loop(self):
        """runがruntime.run_loopを呼び出すことを確認する。"""
        agent = ExecutorAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "Tests passed: 171/171"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get.return_value = None

        result = agent.run(runtime, "run the tests")

        assert runtime.run_loop.called
        assert result == "Tests passed: 171/171"

    def test_run_passes_message(self):
        """runが正しいメッセージをruntime.run_loopに渡すことを確認する。"""
        agent = ExecutorAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get.return_value = None

        agent.run(runtime, "run uv run pytest")

        call_args = runtime.run_loop.call_args
        passed_message = call_args[0][1]
        assert passed_message == "run uv run pytest"

    def test_run_with_context(self):
        """contextを渡してrunが動作することを確認する。"""
        agent = ExecutorAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get.return_value = None

        result = agent.run(runtime, "build docker image", context={"cwd": "/project"})
        assert result == "done"

    def test_run_creates_session_with_system_prompt(self):
        """runがシステムプロンプト付きのセッションを作成することを確認する。"""
        agent = ExecutorAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get.return_value = None

        with patch("ptsu_code.agent.runtime.AgentSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.tool_registry = MagicMock()
            mock_session_class.return_value = mock_session
            agent.run(runtime, "run tests")
            mock_session.add_message.assert_called()
            first_call = mock_session.add_message.call_args_list[0]
            assert first_call[0][0] == "system"

    @pytest.mark.parametrize("message", [
        "run the tests",
        "build the docker image",
        "check if the server is running",
        "execute uv run ruff check",
    ])
    def test_run_various_execute_messages(self, message: str):
        """様々な実行メッセージでrunが動作することを確認する。"""
        agent = ExecutorAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = f"executed: {message}"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get.return_value = None

        result = agent.run(runtime, message)
        assert result == f"executed: {message}"
