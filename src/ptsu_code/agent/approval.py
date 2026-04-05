"""ツール実行の承認フロー管理。"""

from enum import Enum


class ApprovalDecision(Enum):
    """承認の判定結果。"""

    APPROVE = "approve"
    REJECT = "reject"
    ALWAYS_APPROVE = "always_approve"


class ApprovalManager:
    """ツール実行の承認を管理する。"""

    def __init__(self, auto_approve: bool = False) -> None:
        """初期化。

        Args:
            auto_approve: 全てのツールを自動承認する場合 True
        """
        self._auto_approved_tools: set[str] = set()
        self._auto_approve_all = auto_approve

    def needs_approval(self, tool_name: str, requires_approval: bool) -> bool:
        """承認が必要か判定する。

        Args:
            tool_name: ツール名
            requires_approval: ツールが承認を必要とするか

        Returns:
            承認が必要な場合 True
        """
        if self._auto_approve_all:
            return False

        if not requires_approval:
            return False

        if tool_name in self._auto_approved_tools:
            return False

        return True

    def add_auto_approved_tool(self, tool_name: str) -> None:
        """ツールを自動承認リストに追加する。

        Args:
            tool_name: ツール名
        """
        self._auto_approved_tools.add(tool_name)

    def clear_auto_approved_tools(self) -> None:
        """自動承認リストをクリアする。"""
        self._auto_approved_tools.clear()

    def is_auto_approved(self, tool_name: str) -> bool:
        """ツールが自動承認されているか確認する。

        Args:
            tool_name: ツール名

        Returns:
            自動承認されている場合 True
        """
        return tool_name in self._auto_approved_tools or self._auto_approve_all
