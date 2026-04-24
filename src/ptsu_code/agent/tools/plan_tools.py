"""ULTRAPLANモード用プランニングツール。"""

from pathlib import Path

from .base import Tool, ToolDefinition, ToolParameter, ToolResult

_DEFAULT_PLAN_PATH = "/tmp/ptsu-plan.md"


class WritePlanTool(Tool):
    """プランをファイルに書き込むツール。

    ULTRAPLANモードでLLMが計画をMarkdownファイルとして保存するために使用する。
    承認不要（計画ファイルへの書き込みのため）。
    """

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="write_plan",
            description=(
                "計画をMarkdownファイルとして保存する。"
                "ULTRAPLANモードで調査結果をもとにした実装計画を記述するために使用する。"
            ),
            parameters=(
                ToolParameter(
                    name="content",
                    type="string",
                    description="Markdown形式の計画内容",
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description=f"保存先ファイルパス（省略時: {_DEFAULT_PLAN_PATH}）",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: str) -> ToolResult:
        """プランをファイルに書き込む。

        Args:
            content: Markdown形式の計画内容
            path: 保存先ファイルパス（省略時はデフォルト）

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            content = kwargs["content"]
            plan_path = Path(kwargs.get("path") or _DEFAULT_PLAN_PATH)
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"Plan written to {plan_path} ({len(content)} chars)",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write plan: {e}",
            )


class ExitPlanModeTool(Tool):
    """ULTRAPLANモードの終了を宣言するツール。

    LLMが計画の完成を宣言するために呼び出す。
    このツール呼び出しはユーザーの承認を必要とし、
    承認されると plan_approved フラグがセットされる。
    UltraPlanAgentはこのフラグを検出してループを終了する。
    """

    def __init__(self) -> None:
        """初期化。"""
        self._plan_approved: bool = False
        self._approved_plan: str | None = None
        self._plan_path: str = _DEFAULT_PLAN_PATH

    @property
    def requires_approval(self) -> bool:
        """プラン承認のため常にユーザー確認が必要。

        Returns:
            True（常に承認が必要）
        """
        return True

    @property
    def plan_approved(self) -> bool:
        """プランが承認されているかを返す。

        Returns:
            承認済みの場合 True
        """
        return self._plan_approved

    @property
    def approved_plan(self) -> str | None:
        """承認されたプラン内容を返す。

        Returns:
            承認されたプラン内容（未承認の場合 None）
        """
        return self._approved_plan

    def reset(self) -> None:
        """承認状態をリセットする。"""
        self._plan_approved = False
        self._approved_plan = None

    @property
    def definition(self) -> ToolDefinition:
        """ツール定義を返す。

        Returns:
            ツール定義
        """
        return ToolDefinition(
            name="exit_plan_mode",
            description=(
                "計画の完成をユーザーに提示し、承認を求める。"
                "ULTRAPLANモードで調査と計画立案が完了したら必ずこのツールを呼び出す。"
                "ユーザーが承認するとプランニングフェーズが終了し実装が開始される。"
                "ユーザーが却下した場合はフィードバックを受けて計画を改善する。"
            ),
            parameters=(
                ToolParameter(
                    name="summary",
                    type="string",
                    description="ユーザーへの1〜3行の要約（何を実装するか、なぜその方針か）",
                    required=True,
                ),
                ToolParameter(
                    name="plan_path",
                    type="string",
                    description=f"write_planで保存したプランファイルのパス（省略時: {_DEFAULT_PLAN_PATH}）",
                    required=False,
                ),
            ),
        )

    def execute(self, **kwargs: str) -> ToolResult:
        """プランの承認を記録する。

        承認フロー（request_approval_callbackによるy/n確認）を通過した後に呼び出される。

        Args:
            summary: プランの要約
            plan_path: プランファイルのパス

        Returns:
            実行結果
        """
        try:
            self.validate_parameters(**kwargs)
            plan_path = Path(kwargs.get("plan_path") or _DEFAULT_PLAN_PATH)

            plan_content: str = kwargs.get("summary", "")
            if plan_path.exists():
                plan_content = plan_path.read_text(encoding="utf-8")

            self._plan_approved = True
            self._approved_plan = plan_content
            self._plan_path = str(plan_path)

            return ToolResult(
                success=True,
                output=(
                    "Plan approved by user. "
                    "Planning phase complete. "
                    "Respond with exactly: ULTRAPLAN_COMPLETE"
                ),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to exit plan mode: {e}",
            )
