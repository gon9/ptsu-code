"""ファイルツールのテスト。"""



from ptsu_code.agent.tools.file_tools import FileReadTool, FileWriteTool


class TestFileReadTool:
    """FileReadToolクラスのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = FileReadTool()
        definition = tool.definition

        assert definition.name == "read_file"
        assert len(definition.parameters) == 3
        param_names = {p.name for p in definition.parameters}
        assert "path" in param_names
        assert "offset" in param_names
        assert "limit" in param_names

    def test_read_existing_file(self, tmp_path):
        """既存ファイルが読み込めることを確認する。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        tool = FileReadTool()
        result = tool.execute(path=str(test_file))

        assert result.success is True
        assert "Hello, World!" in result.output
        assert "Lines 1-" in result.output
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

    def test_read_with_offset_continuation_hint(self, tmp_path):
        """offset/limit 指定でファイルの途中を読むとき継続ヒントが表示されること。"""
        test_file = tmp_path / "big.txt"
        lines = [f"line{i}" for i in range(1, 21)]
        test_file.write_text("\n".join(lines))

        tool = FileReadTool()
        result = tool.execute(path=str(test_file), offset=1, limit=5)

        assert result.success is True
        assert "offset=" in result.output

    def test_read_exception_returns_error(self, tmp_path):
        """読み込み中に例外が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        with patch("pathlib.Path.read_text", side_effect=OSError("disk error")):
            tool = FileReadTool()
            result = tool.execute(path=str(test_file))

        assert result.success is False
        assert "Failed to read file" in result.error


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

    def test_requires_approval_is_true(self):
        """FileWriteTool.requires_approval が True であること。"""
        tool = FileWriteTool()
        assert tool.requires_approval is True

    def test_write_exception_returns_error(self, tmp_path):
        """書き込み中に例外が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            tool = FileWriteTool()
            result = tool.execute(path=str(tmp_path / "out.txt"), content="data")

        assert result.success is False
        assert "Failed to write file" in result.error
