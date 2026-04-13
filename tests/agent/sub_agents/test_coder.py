"""CoderAgentのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgentConfig
from ptsu_code.agent.sub_agents.coder import CoderAgent


class TestCoderAgentConfig:
    """CoderAgentの設定テスト。"""

    def test_config_role(self):
        """ロールがCODERであることを確認する。"""
        agent = CoderAgent()
        assert agent.config.role == AgentRole.CODER

    def test_config_name(self):
        """名前が正しいことを確認する。"""
        agent = CoderAgent()
        assert agent.config.name == "Coder"

    def test_config_allowed_tools_includes_write(self):
        """allowed_toolsにwrite_fileが含まれることを確認する。"""
        agent = CoderAgent()
        assert "write_file" in agent.config.allowed_tools

    def test_config_allowed_tools_includes_read(self):
        """allowed_toolsにread_fileが含まれることを確認する。"""
        agent = CoderAgent()
        assert "read_file" in agent.config.allowed_tools

    def test_config_allowed_tools_includes_search(self):
        """allowed_toolsに検索ツールが含まれることを確認する。"""
        agent = CoderAgent()
        allowed = agent.config.allowed_tools
        assert "grep_search" in allowed
        assert "find_files" in allowed
        assert "list_directory" in allowed

    def test_config_no_execute_command(self):
        """execute_commandが許可されていないことを確認する。"""
        agent = CoderAgent()
        assert "execute_command" not in agent.config.allowed_tools

    def test_config_temperature(self):
        """temperatureが0.3であることを確認する。"""
        agent = CoderAgent()
        assert agent.config.temperature == 0.3

    def test_config_max_turns(self):
        """max_turnsが10であることを確認する。"""
        agent = CoderAgent()
        assert agent.config.max_turns == 10

    def test_config_returns_subagentconfig_type(self):
        """configがSubAgentConfigを返すことを確認する。"""
        agent = CoderAgent()
        assert isinstance(agent.config, SubAgentConfig)

    def test_system_prompt_mentions_read_before_write(self):
        """システムプロンプトに修正前の読み取り指示が含まれることを確認する。"""
        agent = CoderAgent()
        prompt = agent.config.system_prompt
        assert "read" in prompt.lower()
        assert "write" in prompt.lower()

    def test_system_prompt_mentions_coder(self):
        """システムプロンプトにCoder Agentの説明が含まれることを確認する。"""
        agent = CoderAgent()
        prompt = agent.config.system_prompt
        assert "Coder Agent" in prompt


class TestCoderAgentRun:
    """CoderAgent.runのテスト。"""

    def test_run_calls_runtime_run_loop(self):
        """runがruntime.run_loopを呼び出すことを確認する。"""
        agent = CoderAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "Added new function to src/main.py"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, "add a new function")

        assert runtime.run_loop.called
        assert result == "Added new function to src/main.py"

    def test_run_passes_message(self):
        """runが正しいメッセージをruntime.run_loopに渡すことを確認する。"""
        agent = CoderAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        agent.run(runtime, "fix the login bug")

        call_args = runtime.run_loop.call_args
        passed_message = call_args[0][1]
        assert passed_message == "fix the login bug"

    def test_run_with_context(self):
        """contextを渡してrunが動作することを確認する。"""
        agent = CoderAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, "refactor code", context={"language": "python"})
        assert result == "done"

    def test_run_creates_session_with_system_prompt(self):
        """runがシステムプロンプト付きのセッションを作成することを確認する。"""
        agent = CoderAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "done"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        with patch("ptsu_code.agent.runtime.AgentSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.tool_registry = MagicMock()
            mock_session_class.return_value = mock_session
            agent.run(runtime, "write code")
            mock_session.add_message.assert_called()
            first_call = mock_session.add_message.call_args_list[0]
            assert first_call[0][0] == "system"

    @pytest.mark.parametrize("message", [
        "fix the authentication bug",
        "add a new API endpoint",
        "refactor the database module",
        "write unit tests for UserService",
    ])
    def test_run_various_coding_messages(self, message: str):
        """様々なコーディングメッセージでrunが動作することを確認する。"""
        agent = CoderAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = f"done: {message}"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, message)
        assert result == f"done: {message}"
