"""ファイル操作ツール。"""

from pathlib import Path

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class FileReadTool(Tool):
    """ファイル読み込みツール。"""

    MAX_LINES_PER_READ = 200

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="read_file",
            description=(
                "指定されたパスのファイルを読み込む。"
                f"一度に最大 {self.MAX_LINES_PER_READ} 行。"
                "大きなファイルは offset と limit で範囲指定して読む。"
            ),
            parameters=(
                ToolParameter(
                    name="path",
                    type="string",
                    description="読み込むファイルのパス",
                    required=True,
                ),
                ToolParameter(
                    name="offset",
                    type="integer",
                    description="読み始める行番号（1始まり）。省略時は1",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description=f"読み込む最大行数。省略時は {self.MAX_LINES_PER_READ}",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: str) -> ToolResult:
        """ファイルを読み込む。

        Args:
            path: ファイルパス
            offset: 読み始める行番号（1始まり、省略時は1）
            limit: 読み込む最大行数

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            file_path = Path(kwargs["path"])
            offset = int(kwargs.get("offset") or 1)
            limit = int(kwargs.get("limit") or self.MAX_LINES_PER_READ)

            if not file_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Not a file: {file_path}",
                )

            lines = file_path.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)
            start = max(0, offset - 1)
            end = min(start + limit, total_lines)
            selected = lines[start:end]
            content = "\n".join(selected)

            header = f"[Lines {start + 1}-{end} of {total_lines} total]"
            if end < total_lines:
                header += f" — use offset={end + 1} to continue reading"
            return ToolResult(
                success=True,
                output=f"{header}\n{content}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to read file: {e}",
            )


class FileWriteTool(Tool):
    """ファイル書き込みツール。"""

    @property
    def requires_approval(self) -> bool:
        """ファイル書き込みは破壊的操作のため承認が必要。

        Returns:
            True（常に承認が必要）
        """
        return True

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="write_file",
            description="指定されたパスにファイルを書き込む",
            parameters=(
                ToolParameter(
                    name="path",
                    type="string",
                    description="書き込むファイルのパス",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="書き込む内容",
                    required=True,
                ),
            ),
        )

    def execute(self, **kwargs: str) -> ToolResult:
        """ファイルに書き込む。

        Args:
            path: ファイルパス
            content: 書き込む内容

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            file_path = Path(kwargs["path"])
            content = kwargs["content"]

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Successfully wrote to {file_path}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write file: {e}",
            )
