"""Sub-agent基底クラスのテスト。"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent, SubAgentConfig


class ConcreteSubAgent(SubAgent):
    """テスト用のサブクラス。"""

    _role: AgentRole = AgentRole.GENERAL

    def __init__(self, role: AgentRole = AgentRole.GENERAL) -> None:
        self._role = role

    @property
    def config(self) -> SubAgentConfig:
        return SubAgentConfig(
            role=self._role,
            name="TestAgent",
            description="Test agent for unit tests",
            system_prompt="You are a test agent.",
            allowed_tools=["read_file"],
            max_turns=5,
            temperature=0.5,
        )

    def run(self, runtime: Any, message: str, context: dict[str, Any] | None = None) -> str:
        return f"echo: {message}"


class TestAgentRole:
    """AgentRoleのテスト。"""

    def test_role_values(self):
        """全ロールの値が正しいことを確認する。"""
        assert AgentRole.SEARCHER.value == "searcher"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.EXECUTOR.value == "executor"
        assert AgentRole.GENERAL.value == "general"
        assert AgentRole.ULTRAPLAN.value == "ultraplan"

    def test_role_members(self):
        """全ロールが存在することを確認する。"""
        roles = {r.value for r in AgentRole}
        assert roles == {"searcher", "coder", "executor", "general", "ultraplan"}

    @pytest.mark.parametrize("role", list(AgentRole))
    def test_role_enum_access(self, role: AgentRole):
        """各ロールにEnumとしてアクセスできることを確認する。"""
        assert AgentRole(role.value) == role


class TestSubAgentConfig:
    """SubAgentConfigのテスト。"""

    def test_config_required_fields(self):
        """必須フィールドが正しく設定されることを確認する。"""
        cfg = SubAgentConfig(
            role=AgentRole.SEARCHER,
            name="TestAgent",
            description="Test description",
            system_prompt="System prompt",
        )
        assert cfg.role == AgentRole.SEARCHER
        assert cfg.name == "TestAgent"
        assert cfg.description == "Test description"
        assert cfg.system_prompt == "System prompt"
        assert cfg.allowed_tools == []

    def test_config_default_values(self):
        """デフォルト値が正しいことを確認する。"""
        cfg = SubAgentConfig(
            role=AgentRole.GENERAL,
            name="Agent",
            description="desc",
            system_prompt="prompt",
        )
        assert cfg.max_turns == 10
        assert cfg.temperature is None

    def test_config_custom_values(self):
        """カスタム値が正しく設定されることを確認する。"""
        cfg = SubAgentConfig(
            role=AgentRole.CODER,
            name="Coder",
            description="A coder agent",
            system_prompt="Code agent prompt",
            allowed_tools=["read_file", "write_file"],
            max_turns=3,
            temperature=0.1,
        )
        assert cfg.allowed_tools == ["read_file", "write_file"]
        assert cfg.max_turns == 3
        assert cfg.temperature == 0.1


class TestSubAgentAbstract:
    """SubAgent抽象クラスのテスト。"""

    def test_cannot_instantiate_abstract(self):
        """SubAgentは直接インスタンス化できないことを確認する。"""
        with pytest.raises(TypeError):
            SubAgent()  # type: ignore[abstract]

    def test_concrete_subclass_instantiable(self):
        """具体的なサブクラスはインスタンス化できることを確認する。"""
        agent = ConcreteSubAgent()
        assert agent is not None

    def test_config_property_returns_correct_type(self):
        """configプロパティがSubAgentConfigを返すことを確認する。"""
        agent = ConcreteSubAgent(AgentRole.CODER)
        assert isinstance(agent.config, SubAgentConfig)

    def test_run_returns_string(self):
        """runメソッドが文字列を返すことを確認する。"""
        agent = ConcreteSubAgent()
        runtime = MagicMock()
        result = agent.run(runtime, "hello")
        assert isinstance(result, str)
        assert result == "echo: hello"

    def test_run_with_context(self):
        """contextを渡してrunメソッドが動作することを確認する。"""
        agent = ConcreteSubAgent()
        runtime = MagicMock()
        result = agent.run(runtime, "hello", context={"cwd": "/tmp"})
        assert result == "echo: hello"

    @pytest.mark.parametrize("role", list(AgentRole))
    def test_config_role_matches(self, role: AgentRole):
        """configのroleが正しく反映されることを確認する。"""
        agent = ConcreteSubAgent(role)
        assert agent.config.role == role
