"""検索ツール（Grep, Find, ListDir）。"""

import subprocess
from pathlib import Path
from typing import Any

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class GrepTool(Tool):
    """ファイル内容を検索するツール（grep）。"""

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="grep_search",
            description="ファイル内容をパターン検索する（grep）。正規表現をサポート。",
            parameters=(
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="検索パターン（正規表現）",
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="検索対象のパスまたはディレクトリ",
                    required=True,
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="再帰的に検索するか（デフォルト: true）",
                    required=False,
                ),
                ToolParameter(
                    name="ignore_case",
                    type="boolean",
                    description="大文字小文字を区別しない（デフォルト: false）",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """ツールを実行する。

        Args:
            **kwargs: ツールパラメータ
                - pattern: 検索パターン
                - path: 検索対象パス
                - recursive: 再帰検索（デフォルト: True）
                - ignore_case: 大文字小文字を区別しない（デフォルト: False）

        Returns:
            実行結果
        """
        self.validate_parameters(**kwargs)

        pattern = kwargs["pattern"]
        path = kwargs["path"]
        recursive = kwargs.get("recursive", True)
        ignore_case = kwargs.get("ignore_case", False)

        try:
            # grepコマンドを構築
            cmd = ["grep"]

            if ignore_case:
                cmd.append("-i")

            if recursive:
                cmd.append("-r")

            # 行番号を表示
            cmd.append("-n")

            # パターンとパスを追加
            cmd.extend([pattern, path])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # grepは結果が見つからない場合exit code 1を返す
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=result.stdout,
                    error="",
                )
            elif result.returncode == 1:
                return ToolResult(
                    success=True,
                    output="No matches found",
                    error="",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=result.stderr or "grep command failed",
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error="grep command timed out after 30 seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute grep: {e}",
            )


class FindTool(Tool):
    """ファイル名を検索するツール（find）。"""

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="find_files",
            description="ファイル名やパターンでファイルを検索する（find）",
            parameters=(
                ToolParameter(
                    name="path",
                    type="string",
                    description="検索開始ディレクトリ",
                    required=True,
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="ファイル名パターン（ワイルドカード使用可）",
                    required=False,
                ),
                ToolParameter(
                    name="type",
                    type="string",
                    description="ファイルタイプ（f=ファイル, d=ディレクトリ）",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """ツールを実行する。

        Args:
            **kwargs: ツールパラメータ
                - path: 検索開始ディレクトリ
                - pattern: ファイル名パターン（オプション）
                - type: ファイルタイプ（オプション）

        Returns:
            実行結果
        """
        self.validate_parameters(**kwargs)

        path = kwargs["path"]
        pattern = kwargs.get("pattern")
        file_type = kwargs.get("type")

        try:
            # findコマンドを構築
            cmd = ["find", path]

            if file_type:
                cmd.extend(["-type", file_type])

            if pattern:
                cmd.extend(["-name", pattern])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=result.stdout,
                    error="",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=result.stderr or "find command failed",
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error="find command timed out after 30 seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute find: {e}",
            )


class ListDirTool(Tool):
    """ディレクトリの内容を一覧表示するツール。"""

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="list_directory",
            description="ディレクトリの内容を一覧表示する",
            parameters=(
                ToolParameter(
                    name="path",
                    type="string",
                    description="一覧表示するディレクトリパス",
                    required=True,
                ),
                ToolParameter(
                    name="show_hidden",
                    type="boolean",
                    description="隠しファイルを表示するか（デフォルト: false）",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """ツールを実行する。

        Args:
            **kwargs: ツールパラメータ
                - path: ディレクトリパス
                - show_hidden: 隠しファイルを表示（デフォルト: False）

        Returns:
            実行結果
        """
        self.validate_parameters(**kwargs)

        path = kwargs["path"]
        show_hidden = kwargs.get("show_hidden", False)

        try:
            dir_path = Path(path)

            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Directory not found: {path}",
                )

            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Not a directory: {path}",
                )

            # ディレクトリ内容を取得
            entries = []
            for entry in sorted(dir_path.iterdir()):
                # 隠しファイルのフィルタリング
                if not show_hidden and entry.name.startswith("."):
                    continue

                # ファイルタイプと情報を取得
                if entry.is_dir():
                    entry_type = "DIR"
                    size = "-"
                elif entry.is_file():
                    entry_type = "FILE"
                    size = f"{entry.stat().st_size:,} bytes"
                else:
                    entry_type = "OTHER"
                    size = "-"

                entries.append(f"{entry_type:6} {size:>15}  {entry.name}")

            if not entries:
                output = "Directory is empty"
            else:
                output = "\n".join(entries)

            return ToolResult(
                success=True,
                output=output,
                error="",
            )

        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to list directory: {e}",
            )
