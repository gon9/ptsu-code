"""コマンド実行ツール。"""

import subprocess
from typing import Any

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class CommandExecutionTool(Tool):
    """コマンド実行ツール。"""

    def __init__(self, timeout: int = 30) -> None:
        """初期化。

        Args:
            timeout: コマンド実行のタイムアウト秒数
        """
        self.timeout = timeout

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="execute_command",
            description="シェルコマンドを実行する",
            parameters=(
                ToolParameter(
                    name="command",
                    type="string",
                    description="実行するコマンド",
                    required=True,
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="作業ディレクトリ",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """コマンドを実行する。

        Args:
            command: 実行するコマンド
            cwd: 作業ディレクトリ（オプション）

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            command = kwargs["command"]
            cwd = kwargs.get("cwd")

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd,
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=result.stdout,
                )
            else:
                return ToolResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr,
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {self.timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {e}",
            )
