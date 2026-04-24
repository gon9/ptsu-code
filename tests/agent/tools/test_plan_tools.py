"""plan_toolsのテスト。"""



from ptsu_code.agent.tools.plan_tools import ExitPlanModeTool, WritePlanTool


class TestWritePlanTool:
    """WritePlanToolのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = WritePlanTool()
        d = tool.definition
        assert d.name == "write_plan"
        param_names = {p.name for p in d.parameters}
        assert "content" in param_names
        assert "path" in param_names

    def test_requires_no_approval(self):
        """承認不要であることを確認する。"""
        tool = WritePlanTool()
        assert tool.requires_approval is False

    def test_write_to_default_path(self, tmp_path):
        """デフォルトパスへ書き込みが成功することを確認する。"""
        tool = WritePlanTool()
        plan_file = tmp_path / "ptsu-plan.md"
        result = tool.execute(content="# My Plan\n\nStep 1", path=str(plan_file))
        assert result.success is True
        assert plan_file.read_text() == "# My Plan\n\nStep 1"
        assert "Plan written to" in result.output

    def test_write_creates_parent_dirs(self, tmp_path):
        """親ディレクトリが存在しない場合も自動作成することを確認する。"""
        tool = WritePlanTool()
        plan_file = tmp_path / "nested" / "deep" / "plan.md"
        result = tool.execute(content="content", path=str(plan_file))
        assert result.success is True
        assert plan_file.exists()

    def test_missing_required_param(self):
        """必須パラメータが不足している場合はエラーになることを確認する。"""
        tool = WritePlanTool()
        result = tool.execute()
        assert result.success is False
        assert result.error is not None


class TestExitPlanModeTool:
    """ExitPlanModeToolのテスト。"""

    def test_definition(self):
        """ツール定義が正しいことを確認する。"""
        tool = ExitPlanModeTool()
        d = tool.definition
        assert d.name == "exit_plan_mode"
        param_names = {p.name for p in d.parameters}
        assert "summary" in param_names

    def test_requires_approval(self):
        """承認が必要であることを確認する。"""
        tool = ExitPlanModeTool()
        assert tool.requires_approval is True

    def test_initial_state(self):
        """初期状態でplan_approvedがFalseであることを確認する。"""
        tool = ExitPlanModeTool()
        assert tool.plan_approved is False
        assert tool.approved_plan is None

    def test_execute_sets_plan_approved(self, tmp_path):
        """executeが承認フラグをセットすることを確認する。"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\nDo something")
        tool = ExitPlanModeTool()
        result = tool.execute(summary="Do something", plan_path=str(plan_file))
        assert result.success is True
        assert tool.plan_approved is True
        assert tool.approved_plan == "# Plan\n\nDo something"
        assert "ULTRAPLAN_COMPLETE" in result.output

    def test_execute_uses_summary_if_no_file(self):
        """プランファイルが存在しない場合はsummaryを使うことを確認する。"""
        tool = ExitPlanModeTool()
        result = tool.execute(
            summary="My fallback summary",
            plan_path="/tmp/nonexistent_ptsu_plan_xyz.md",
        )
        assert result.success is True
        assert tool.plan_approved is True
        assert tool.approved_plan == "My fallback summary"

    def test_reset_clears_state(self, tmp_path):
        """resetが承認状態をクリアすることを確認する。"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("content")
        tool = ExitPlanModeTool()
        tool.execute(summary="summary", plan_path=str(plan_file))
        assert tool.plan_approved is True
        tool.reset()
        assert tool.plan_approved is False
        assert tool.approved_plan is None

    def test_missing_required_param(self):
        """必須パラメータが不足している場合はエラーになることを確認する。"""
        tool = ExitPlanModeTool()
        result = tool.execute()
        assert result.success is False
        assert result.error is not None
