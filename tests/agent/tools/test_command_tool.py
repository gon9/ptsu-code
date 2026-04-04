"""コマンドツールのテスト。"""


from ptsu_code.agent.tools.command_tool import CommandExecutionTool


class TestCommandExecutionTool:
    """CommandExecutionToolクラスのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = CommandExecutionTool()
        definition = tool.definition

        assert definition.name == "execute_command"
        assert len(definition.parameters) == 2
        param_names = {p.name for p in definition.parameters}
        assert "command" in param_names
        assert "cwd" in param_names

    def test_execute_successful_command(self):
        """成功するコマンドが実行できることを確認する。"""
        tool = CommandExecutionTool()
        result = tool.execute(command="echo 'Hello'")

        assert result.success is True
        assert "Hello" in result.output

    def test_execute_failed_command(self):
        """失敗するコマンドがエラーを返すことを確認する。"""
        tool = CommandExecutionTool()
        result = tool.execute(command="exit 1")

        assert result.success is False

    def test_execute_with_cwd(self, tmp_path):
        """作業ディレクトリを指定してコマンドが実行できることを確認する。"""
        tool = CommandExecutionTool()
        result = tool.execute(command="pwd", cwd=str(tmp_path))

        assert result.success is True
        assert str(tmp_path) in result.output

    def test_execute_timeout(self):
        """タイムアウトが正しく動作することを確認する。"""
        tool = CommandExecutionTool(timeout=1)
        result = tool.execute(command="sleep 5")

        assert result.success is False
        assert "timed out" in result.error.lower()
