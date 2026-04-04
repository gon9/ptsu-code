"""ツール基底クラスのテスト。"""

import pytest

from ptsu_code.agent.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult


class TestToolParameter:
    """ToolParameterクラスのテスト。"""

    def test_create_required_parameter(self):
        """必須パラメータが作成できることを確認する。"""
        param = ToolParameter(name="path", type="string", description="File path", required=True)
        assert param.name == "path"
        assert param.type == "string"
        assert param.description == "File path"
        assert param.required is True

    def test_create_optional_parameter(self):
        """オプションパラメータが作成できることを確認する。"""
        param = ToolParameter(name="timeout", type="number", description="Timeout", required=False)
        assert param.required is False


class TestToolDefinition:
    """ToolDefinitionクラスのテスト。"""

    def test_to_openai_schema(self):
        """OpenAIスキーマに正しく変換されることを確認する。"""
        definition = ToolDefinition(
            name="test_tool",
            description="Test tool",
            parameters=(
                ToolParameter(name="param1", type="string", description="Param 1", required=True),
                ToolParameter(name="param2", type="number", description="Param 2", required=False),
            ),
        )

        schema = definition.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test_tool"
        assert schema["function"]["description"] == "Test tool"
        assert "param1" in schema["function"]["parameters"]["properties"]
        assert "param2" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["param1"]


class TestToolResult:
    """ToolResultクラスのテスト。"""

    @pytest.mark.parametrize(
        ("success", "output", "error"),
        [
            (True, "Success output", None),
            (False, "", "Error message"),
            (False, "Partial output", "Error occurred"),
        ],
    )
    def test_create_tool_result(self, success, output, error):
        """ツール実行結果が正しく作成されることを確認する。"""
        result = ToolResult(success=success, output=output, error=error)
        assert result.success == success
        assert result.output == output
        assert result.error == error


class MockTool(Tool):
    """テスト用のモックツール。"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="mock_tool",
            description="Mock tool for testing",
            parameters=(ToolParameter(name="input", type="string", description="Input", required=True),),
        )

    def execute(self, **kwargs):
        return ToolResult(success=True, output=f"Executed with {kwargs}")


class TestTool:
    """Toolクラスのテスト。"""

    def test_validate_parameters_success(self):
        """パラメータバリデーションが成功することを確認する。"""
        tool = MockTool()
        tool.validate_parameters(input="test")

    def test_validate_parameters_missing(self):
        """必須パラメータが不足している場合にエラーになることを確認する。"""
        tool = MockTool()
        with pytest.raises(ValueError, match="Missing required parameters"):
            tool.validate_parameters()

    def test_execute(self):
        """ツールが実行できることを確認する。"""
        tool = MockTool()
        result = tool.execute(input="test")
        assert result.success is True
        assert "test" in result.output
