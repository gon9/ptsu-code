"""検索ツールのテスト。"""



from ptsu_code.agent.tools.search_tools import FindTool, GrepTool, ListDirTool


class TestGrepTool:
    """GrepToolのテストクラス。"""

    def test_definition(self):
        """ツール定義のテスト。"""
        tool = GrepTool()
        definition = tool.definition

        assert definition.name == "grep_search"
        assert "grep" in definition.description.lower()
        assert len(definition.parameters) == 4

    def test_grep_search_found(self, tmp_path):
        """パターンが見つかる場合のテスト。"""
        # テストファイルを作成
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nPython is great\nHello Python")

        tool = GrepTool()
        result = tool.execute(pattern="Python", path=str(test_file), recursive=False)

        assert result.success is True
        assert "Python" in result.output
        assert result.error == ""

    def test_grep_search_not_found(self, tmp_path):
        """パターンが見つからない場合のテスト。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        tool = GrepTool()
        result = tool.execute(pattern="NotFound", path=str(test_file), recursive=False)

        assert result.success is True
        assert "No matches found" in result.output

    def test_grep_search_ignore_case(self, tmp_path):
        """大文字小文字を区別しない検索のテスト。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        tool = GrepTool()
        result = tool.execute(
            pattern="hello", path=str(test_file), recursive=False, ignore_case=True
        )

        assert result.success is True
        assert "Hello" in result.output

    def test_grep_search_recursive(self, tmp_path):
        """再帰検索のテスト。"""
        # サブディレクトリとファイルを作成
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test.txt").write_text("Python code")

        tool = GrepTool()
        result = tool.execute(pattern="Python", path=str(tmp_path), recursive=True)

        assert result.success is True
        assert "Python" in result.output

    def test_grep_command_failure(self, tmp_path):
        """grep コマンドが失敗した場合（returncode > 1）に success=False を返すこと。"""
        from unittest.mock import MagicMock, patch

        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "grep: invalid option"

        with patch("subprocess.run", return_value=mock_result):
            tool = GrepTool()
            result = tool.execute(pattern="x", path=str(tmp_path))

        assert result.success is False
        assert "grep" in result.error.lower()

    def test_grep_timeout(self, tmp_path):
        """grep がタイムアウトした場合に success=False を返すこと。"""
        import subprocess
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="grep", timeout=30)):
            tool = GrepTool()
            result = tool.execute(pattern="x", path=str(tmp_path))

        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_grep_unexpected_exception(self, tmp_path):
        """予期しない例外が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=OSError("no such file")):
            tool = GrepTool()
            result = tool.execute(pattern="x", path=str(tmp_path))

        assert result.success is False
        assert "Failed to execute grep" in result.error


class TestFindTool:
    """FindToolのテストクラス。"""

    def test_definition(self):
        """ツール定義のテスト。"""
        tool = FindTool()
        definition = tool.definition

        assert definition.name == "find_files"
        assert "find" in definition.description.lower()
        assert len(definition.parameters) == 3

    def test_find_all_files(self, tmp_path):
        """全ファイルを検索するテスト。"""
        # テストファイルを作成
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").touch()

        tool = FindTool()
        result = tool.execute(path=str(tmp_path))

        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.py" in result.output
        assert "file3.txt" in result.output

    def test_find_with_pattern(self, tmp_path):
        """パターン指定でファイルを検索するテスト。"""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()

        tool = FindTool()
        result = tool.execute(path=str(tmp_path), pattern="*.txt")

        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.py" not in result.output

    def test_find_files_only(self, tmp_path):
        """ファイルのみを検索するテスト。"""
        (tmp_path / "file.txt").touch()
        (tmp_path / "subdir").mkdir()

        tool = FindTool()
        result = tool.execute(path=str(tmp_path), type="f")

        assert result.success is True
        assert "file.txt" in result.output
        assert "subdir" not in result.output or result.output.count("subdir") == 0

    def test_find_directories_only(self, tmp_path):
        """ディレクトリのみを検索するテスト。"""
        (tmp_path / "file.txt").touch()
        (tmp_path / "subdir").mkdir()

        tool = FindTool()
        result = tool.execute(path=str(tmp_path), type="d")

        assert result.success is True
        assert "subdir" in result.output

    def test_find_command_failure(self, tmp_path):
        """find コマンドが失敗した場合に success=False を返すこと。"""
        from unittest.mock import MagicMock, patch

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "find: permission denied"

        with patch("subprocess.run", return_value=mock_result):
            tool = FindTool()
            result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "find" in result.error.lower()

    def test_find_timeout(self, tmp_path):
        """find がタイムアウトした場合に success=False を返すこと。"""
        import subprocess
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="find", timeout=30)):
            tool = FindTool()
            result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "timed out" in result.error.lower()

    def test_find_unexpected_exception(self, tmp_path):
        """予期しない例外が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=OSError("bad")):
            tool = FindTool()
            result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "Failed to execute find" in result.error


class TestListDirTool:
    """ListDirToolのテストクラス。"""

    def test_definition(self):
        """ツール定義のテスト。"""
        tool = ListDirTool()
        definition = tool.definition

        assert definition.name == "list_directory"
        assert "ディレクトリ" in definition.description or "directory" in definition.description.lower()
        assert len(definition.parameters) == 2

    def test_list_directory(self, tmp_path):
        """ディレクトリ一覧のテスト。"""
        # テストファイルを作成
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.py").write_text("test")
        (tmp_path / "subdir").mkdir()

        tool = ListDirTool()
        result = tool.execute(path=str(tmp_path))

        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.py" in result.output
        assert "subdir" in result.output
        assert "FILE" in result.output
        assert "DIR" in result.output

    def test_list_directory_with_hidden(self, tmp_path):
        """隠しファイルを含むディレクトリ一覧のテスト。"""
        (tmp_path / "visible.txt").touch()
        (tmp_path / ".hidden").touch()

        tool = ListDirTool()

        # 隠しファイルなし
        result = tool.execute(path=str(tmp_path), show_hidden=False)
        assert result.success is True
        assert "visible.txt" in result.output
        assert ".hidden" not in result.output

        # 隠しファイルあり
        result = tool.execute(path=str(tmp_path), show_hidden=True)
        assert result.success is True
        assert "visible.txt" in result.output
        assert ".hidden" in result.output

    def test_list_nonexistent_directory(self):
        """存在しないディレクトリのテスト。"""
        tool = ListDirTool()
        result = tool.execute(path="/nonexistent/path")

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_list_file_instead_of_directory(self, tmp_path):
        """ファイルを指定した場合のテスト。"""
        test_file = tmp_path / "file.txt"
        test_file.touch()

        tool = ListDirTool()
        result = tool.execute(path=str(test_file))

        assert result.success is False
        assert "not a directory" in result.error.lower()

    def test_list_empty_directory(self, tmp_path):
        """空のディレクトリのテスト。"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        tool = ListDirTool()
        result = tool.execute(path=str(empty_dir))

        assert result.success is True
        assert "empty" in result.output.lower()

    def test_list_permission_error(self, tmp_path):
        """PermissionError が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        with patch("pathlib.Path.iterdir", side_effect=PermissionError("denied")):
            tool = ListDirTool()
            result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "Permission denied" in result.error

    def test_list_unexpected_exception(self, tmp_path):
        """予期しない例外が発生した場合に success=False を返すこと。"""
        from unittest.mock import patch

        with patch("pathlib.Path.iterdir", side_effect=OSError("disk error")):
            tool = ListDirTool()
            result = tool.execute(path=str(tmp_path))

        assert result.success is False
        assert "Failed to list directory" in result.error

    def test_list_symlink_shown_as_other(self, tmp_path):
        """シンボリックリンクなど is_dir/is_file でない項目が OTHER として表示されること。"""
        from unittest.mock import MagicMock, patch

        mock_entry = MagicMock()
        mock_entry.name = "symlink_entry"
        mock_entry.is_dir.return_value = False
        mock_entry.is_file.return_value = False

        with patch("pathlib.Path.iterdir", return_value=iter([mock_entry])):
            tool = ListDirTool()
            result = tool.execute(path=str(tmp_path), show_hidden=True)

        assert result.success is True
        assert "OTHER" in result.output
