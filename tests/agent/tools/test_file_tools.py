"""ファイルツールのテスト。"""



from ptsu_code.agent.tools.file_tools import FileReadTool, FileWriteTool


class TestFileReadTool:
    """FileReadToolクラスのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = FileReadTool()
        definition = tool.definition

        assert definition.name == "read_file"
        assert len(definition.parameters) == 1
        assert definition.parameters[0].name == "path"

    def test_read_existing_file(self, tmp_path):
        """既存ファイルが読み込めることを確認する。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = FileReadTool()
        result = tool.execute(path=str(test_file))

        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.error is None

    def test_read_nonexistent_file(self, tmp_path):
        """存在しないファイルを読むとエラーになることを確認する。"""
        tool = FileReadTool()
        result = tool.execute(path=str(tmp_path / "nonexistent.txt"))

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_read_directory(self, tmp_path):
        """ディレクトリを読むとエラーになることを確認する。"""
        tool = FileReadTool()
        result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "not a file" in result.error.lower()


class TestFileWriteTool:
    """FileWriteToolクラスのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = FileWriteTool()
        definition = tool.definition

        assert definition.name == "write_file"
        assert len(definition.parameters) == 2
        param_names = {p.name for p in definition.parameters}
        assert "path" in param_names
        assert "content" in param_names

    def test_write_file(self, tmp_path):
        """ファイルが書き込めることを確認する。"""
        test_file = tmp_path / "output.txt"
        tool = FileWriteTool()

        result = tool.execute(path=str(test_file), content="Test content")

        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == "Test content"

    def test_write_file_creates_directory(self, tmp_path):
        """親ディレクトリが自動作成されることを確認する。"""
        test_file = tmp_path / "subdir" / "output.txt"
        tool = FileWriteTool()

        result = tool.execute(path=str(test_file), content="Test content")

        assert result.success is True
        assert test_file.exists()
        assert test_file.parent.exists()

    def test_write_file_overwrites(self, tmp_path):
        """既存ファイルが上書きされることを確認する。"""
        test_file = tmp_path / "output.txt"
        test_file.write_text("Old content")

        tool = FileWriteTool()
        result = tool.execute(path=str(test_file), content="New content")

        assert result.success is True
        assert test_file.read_text() == "New content"
