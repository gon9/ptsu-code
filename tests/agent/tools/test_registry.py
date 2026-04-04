"""ツールレジストリのテスト。"""

import pytest

from ptsu_code.agent.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult
from ptsu_code.agent.tools.registry import ToolRegistry, ToolRegistryError


class SimpleTool(Tool):
    """テスト用のシンプルなツール。"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="simple_tool",
            description="Simple test tool",
            parameters=(ToolParameter(name="value", type="string", description="Value", required=True),),
        )

    def execute(self, **kwargs):
        return ToolResult(success=True, output=f"Value: {kwargs['value']}")


class TestToolRegistry:
    """ToolRegistryクラスのテスト。"""

    def test_register_tool(self):
        """ツールが登録できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        assert len(registry) == 1
        assert "simple_tool" in registry

    def test_register_duplicate_tool(self):
        """同名のツールを登録するとエラーになることを確認する。"""
        registry = ToolRegistry()
        tool1 = SimpleTool()
        tool2 = SimpleTool()

        registry.register(tool1)
        with pytest.raises(ToolRegistryError, match="already registered"):
            registry.register(tool2)

    def test_get_tool(self):
        """ツールが取得できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        retrieved = registry.get("simple_tool")
        assert retrieved is not None
        assert retrieved.definition.name == "simple_tool"

    def test_get_nonexistent_tool(self):
        """存在しないツールを取得するとNoneが返ることを確認する。"""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all_tools(self):
        """全てのツールが取得できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        tools = registry.get_all()
        assert len(tools) == 1
        assert tools[0].definition.name == "simple_tool"

    def test_get_definitions(self):
        """全てのツール定義が取得できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        definitions = registry.get_definitions()
        assert len(definitions) == 1
        assert definitions[0].name == "simple_tool"

    def test_get_openai_schemas(self):
        """OpenAIスキーマが取得できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        schemas = registry.get_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "simple_tool"

    def test_execute_tool(self):
        """ツールが実行できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        result = registry.execute("simple_tool", value="test")
        assert result.success is True
        assert "test" in result.output

    def test_execute_nonexistent_tool(self):
        """存在しないツールを実行するとエラーになることを確認する。"""
        registry = ToolRegistry()
        with pytest.raises(ToolRegistryError, match="not found"):
            registry.execute("nonexistent", value="test")

    def test_clear(self):
        """全てのツールが削除できることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        registry.clear()
        assert len(registry) == 0

    def test_contains(self):
        """ツールの存在確認ができることを確認する。"""
        registry = ToolRegistry()
        tool = SimpleTool()
        registry.register(tool)

        assert "simple_tool" in registry
        assert "nonexistent" not in registry
