"""ApprovalManagerのテスト。"""

import pytest

from ptsu_code.agent.approval import ApprovalDecision, ApprovalManager


class TestApprovalManager:
    """ApprovalManagerのテストクラス。"""

    def test_init_default(self):
        """デフォルト初期化のテスト。"""
        manager = ApprovalManager()
        assert manager._auto_approve_all is False
        assert len(manager._auto_approved_tools) == 0

    def test_init_auto_approve(self):
        """自動承認モードでの初期化のテスト。"""
        manager = ApprovalManager(auto_approve=True)
        assert manager._auto_approve_all is True

    def test_needs_approval_auto_approve_all(self):
        """全自動承認モードでは承認不要。"""
        manager = ApprovalManager(auto_approve=True)
        assert manager.needs_approval("write_file", requires_approval=True) is False

    def test_needs_approval_not_required(self):
        """ツールが承認不要な場合。"""
        manager = ApprovalManager()
        assert manager.needs_approval("read_file", requires_approval=False) is False

    def test_needs_approval_required(self):
        """ツールが承認必要な場合。"""
        manager = ApprovalManager()
        assert manager.needs_approval("write_file", requires_approval=True) is True

    def test_needs_approval_auto_approved_tool(self):
        """ツールが自動承認リストにある場合。"""
        manager = ApprovalManager()
        manager.add_auto_approved_tool("write_file")
        assert manager.needs_approval("write_file", requires_approval=True) is False

    def test_add_auto_approved_tool(self):
        """自動承認ツールの追加。"""
        manager = ApprovalManager()
        manager.add_auto_approved_tool("write_file")
        assert "write_file" in manager._auto_approved_tools
        assert manager.is_auto_approved("write_file") is True

    def test_clear_auto_approved_tools(self):
        """自動承認リストのクリア。"""
        manager = ApprovalManager()
        manager.add_auto_approved_tool("write_file")
        manager.add_auto_approved_tool("execute_command")
        
        manager.clear_auto_approved_tools()
        
        assert len(manager._auto_approved_tools) == 0
        assert manager.is_auto_approved("write_file") is False

    def test_is_auto_approved(self):
        """自動承認チェック。"""
        manager = ApprovalManager()
        assert manager.is_auto_approved("write_file") is False
        
        manager.add_auto_approved_tool("write_file")
        assert manager.is_auto_approved("write_file") is True
        assert manager.is_auto_approved("execute_command") is False

    def test_is_auto_approved_with_auto_approve_all(self):
        """全自動承認モードでの自動承認チェック。"""
        manager = ApprovalManager(auto_approve=True)
        assert manager.is_auto_approved("any_tool") is True
