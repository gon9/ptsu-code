"""Searcher Agentのテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgentConfig
from ptsu_code.agent.sub_agents.searcher import SearcherAgent


class TestSearcherAgentConfig:
    """SearcherAgentの設定テスト。"""

    def test_config_role(self):
        """ロールがSEARCHERであることを確認する。"""
        agent = SearcherAgent()
        assert agent.config.role == AgentRole.SEARCHER

    def test_config_name(self):
        """名前が正しいことを確認する。"""
        agent = SearcherAgent()
        assert agent.config.name == "Searcher"

    def test_config_allowed_tools(self):
        """allowed_toolsに読み取り専用ツールのみが含まれることを確認する。"""
        agent = SearcherAgent()
        allowed = agent.config.allowed_tools
        assert "read_file" in allowed
        assert "grep_search" in allowed
        assert "find_files" in allowed
        assert "list_directory" in allowed

    def test_config_no_write_tools(self):
        """write_fileやexecute_commandが許可されていないことを確認する。"""
        agent = SearcherAgent()
        allowed = agent.config.allowed_tools
        assert "write_file" not in allowed
        assert "execute_command" not in allowed

    def test_config_temperature(self):
        """temperatureがNone（モデルデフォルト使用）であることを確認する。"""
        agent = SearcherAgent()
        assert agent.config.temperature is None

    def test_config_max_turns(self):
        """max_turnsが5であることを確認する。"""
        agent = SearcherAgent()
        assert agent.config.max_turns == 5

    def test_config_returns_subagentconfig_type(self):
        """configがSubAgentConfigを返すことを確認する。"""
        agent = SearcherAgent()
        assert isinstance(agent.config, SubAgentConfig)

    def test_system_prompt_contains_key_instructions(self):
        """システムプロンプトに重要な指示が含まれることを確認する。"""
        agent = SearcherAgent()
        prompt = agent.config.system_prompt
        assert "DO NOT modify" in prompt
        assert "DO NOT execute" in prompt
        assert "Searcher Agent" in prompt

    def test_system_prompt_lists_tools(self):
        """システムプロンプトにツールのリストが含まれることを確認する。"""
        agent = SearcherAgent()
        prompt = agent.config.system_prompt
        assert "read_file" in prompt
        assert "grep_search" in prompt
        assert "find_files" in prompt
        assert "list_directory" in prompt


class TestSearcherAgentRun:
    """SearcherAgent.runのテスト。"""

    def test_run_calls_runtime_run_loop(self):
        """runがruntime.run_loopを呼び出すことを確認する。"""
        agent = SearcherAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "Found: src/main.py line 42"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, "find the main file")

        assert runtime.run_loop.called
        assert result == "Found: src/main.py line 42"

    def test_run_passes_message(self):
        """runが正しいメッセージをruntime.run_loopに渡すことを確認する。"""
        agent = SearcherAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "result"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        agent.run(runtime, "search for User class")

        call_args = runtime.run_loop.call_args
        passed_message = call_args[0][1]
        assert passed_message == "search for User class"

    def test_run_with_context(self):
        """contextを渡してrunが動作することを確認する。"""
        agent = SearcherAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "result"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, "find config", context={"cwd": "/project", "language": "python"})
        assert result == "result"

    def test_run_creates_session_with_system_prompt(self):
        """runがシステムプロンプト付きのセッションを作成することを確認する。"""
        agent = SearcherAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = "result"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None


        with patch("ptsu_code.agent.runtime.AgentSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.tool_registry = MagicMock()
            mock_session_class.return_value = mock_session
            agent.run(runtime, "search")
            mock_session.add_message.assert_called()
            first_call = mock_session.add_message.call_args_list[0]
            assert first_call[0][0] == "system"

    @pytest.mark.parametrize("message", [
        "where is the authentication logic",
        "find all tests",
        "show the directory structure",
        "read README.md",
    ])
    def test_run_various_search_messages(self, message: str):
        """様々な検索メッセージでrunが動作することを確認する。"""
        agent = SearcherAgent()
        runtime = MagicMock()
        runtime.run_loop.return_value = f"result for: {message}"
        runtime.session_tool_registry = MagicMock()
        runtime.session_tool_registry.get_tool.return_value = None

        result = agent.run(runtime, message)
        assert result == f"result for: {message}"
