"""コマンド実行ツール。"""

import subprocess
from typing import Any

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class CommandExecutionTool(Tool):
    """コマンド実行ツール。

    タイムアウト時は自動的にプロセスをkillします。
    """

    def __init__(self, timeout: int = 30) -> None:
        """初期化。

        Args:
            timeout: コマンド実行のタイムアウト秒数（デフォルト: 30秒）
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
            description="シェルコマンドを実行する（タイムアウト時は自動的にプロセスをkill）",
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

        タイムアウト時はプロセスを強制終了（SIGKILL）します。

        Args:
            command: 実行するコマンド
            cwd: 作業ディレクトリ（オプション）

        Returns:
            実行結果
        """
        process = None
        try:
            self.validate_parameters(**kwargs)
            command = kwargs["command"]
            cwd = kwargs.get("cwd")

            # Popenを使用してプロセスを明示的に管理
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
            )

            # タイムアウト付きで完了を待つ
            stdout, stderr = process.communicate(timeout=self.timeout)

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout,
                )
            else:
                return ToolResult(
                    success=False,
                    output=stdout,
                    error=stderr or f"Command exited with code {process.returncode}",
                )

        except subprocess.TimeoutExpired:
            # タイムアウト時はプロセスを強制終了
            if process:
                try:
                    # まずSIGTERMで終了を試みる
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                        killed_msg = "Process terminated (SIGTERM)"
                    except subprocess.TimeoutExpired:
                        # SIGTERMで終了しない場合はSIGKILLで強制終了
                        process.kill()
                        process.wait()
                        killed_msg = "Process killed (SIGKILL)"
                except Exception as kill_error:
                    killed_msg = f"Failed to kill process: {kill_error}"

                # 部分的な出力を取得
                try:
                    stdout, stderr = process.communicate(timeout=0.1)
                    partial_output = stdout if stdout else ""
                except Exception:
                    partial_output = ""

                return ToolResult(
                    success=False,
                    output=partial_output,
                    error=f"Command timed out after {self.timeout} seconds. {killed_msg}",
                )

            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {self.timeout} seconds (process not started)",
            )

        except Exception as e:
            # その他のエラー時もプロセスをクリーンアップ
            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait()
                except Exception:
                    pass

            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {e}",
            )
