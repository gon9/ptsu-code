"""Session Memory 関連のツール。

/summary コマンドとして使用する。
"""

from typing import Any

from ptsu_code.agent.tools.base import Tool, ToolDefinition, ToolResult
from ptsu_code.memory.manager import SessionMemoryManager


class MemorySummaryTool(Tool):
    """セッションメモリを手動で抽出・保存するツール。

    LLM が自律的に呼び出せるほか、ユーザーが '/summary' と入力した場合にも
    直接呼び出される。
    """

    def __init__(self, memory_manager: SessionMemoryManager) -> None:
        """初期化。

        Args:
            memory_manager: 操作対象の SessionMemoryManager
        """
        self._manager = memory_manager

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義。"""
        return ToolDefinition(
            name="memory_summary",
            description=(
                "Manually extract and save session memory. "
                "Call this when the user asks to summarize the session, "
                "save progress, or when important information should be persisted."
            ),
            parameters=(),
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        """セッションメモリを手動で抽出する。

        Args:
            **kwargs: 未使用（引数なしツール）

        Returns:
            実行結果。保存先パスを含む
        """
        success = self._manager.force_extract()
        if success:
            path = self._manager.storage.current_path
            return ToolResult(
                success=True,
                output=f"Session memory saved: {path}",
            )
        return ToolResult(
            success=False,
            output="No conversation to summarize yet.",
            error="Empty conversation",
        )
