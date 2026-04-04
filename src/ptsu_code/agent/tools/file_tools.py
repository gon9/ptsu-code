"""ファイル操作ツール。"""

from pathlib import Path

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class FileReadTool(Tool):
    """ファイル読み込みツール。"""

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="read_file",
            description="指定されたパスのファイルを読み込む",
            parameters=(
                ToolParameter(
                    name="path",
                    type="string",
                    description="読み込むファイルのパス",
                    required=True,
                ),
            ),
        )

    def execute(self, **kwargs: str) -> ToolResult:
        """ファイルを読み込む。

        Args:
            path: ファイルパス

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            file_path = Path(kwargs["path"])

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

            content = file_path.read_text(encoding="utf-8")
            return ToolResult(
                success=True,
                output=content,
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
