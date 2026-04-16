"""コマンド実行・テストに特化したSub-agent。"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent, SubAgentConfig

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime


class ExecutorAgent(SubAgent):
    """コマンド実行・テストを担当するSub-agent。

    execute_command を使いコマンドを実行し、結果を分析して報告する。
    execute_command は承認フロー付きで安全に実行される。
    """

    @property
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""
        return SubAgentConfig(
            role=AgentRole.EXECUTOR,
            name="Executor",
            description="Runs shell commands, tests, and builds to execute tasks",
            system_prompt=self._get_system_prompt(),
            allowed_tools=["execute_command", "read_file"],
            max_turns=5,
            temperature=None,
        )

    def run(
        self,
        runtime: "AgentRuntime",
        message: str,
        context: dict[str, Any] | None = None,
        request_approval_callback: Callable | None = None,
        show_progress_callback: Callable | None = None,
    ) -> str:
        """コマンド実行タスクを実行する。

        Args:
            runtime: AgentRuntimeインスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）

        Returns:
            実行結果
        """
        from ptsu_code.agent.runtime import AgentSession
        from ptsu_code.agent.tools.registry import ToolRegistry

        cfg = self.config

        restricted_registry = ToolRegistry()
        for tool_name in cfg.allowed_tools:
            tool = runtime.session_tool_registry.get(tool_name) if hasattr(runtime, "session_tool_registry") else None
            if tool is not None:
                restricted_registry.register(tool)

        session = AgentSession(
            tool_registry=restricted_registry,
            model=None,
            max_turns=cfg.max_turns,
            temperature=cfg.temperature,
        )
        session.add_message("system", cfg.system_prompt)

        if context:
            context_lines = [f"{k}: {v}" for k, v in context.items()]
            session.add_message("system", "Context:\n" + "\n".join(context_lines))

        return runtime.run_loop(session, message, request_approval_callback, show_progress_callback)

    def _get_system_prompt(self) -> str:
        """システムプロンプトを返す。"""
        return """You are an Executor Agent specialized in running commands and tests.

Your role:
- Execute shell commands to run tests, builds, or other tasks
- Analyze command output and report results clearly
- Handle errors by reading logs and retrying with corrected commands
- DO NOT modify source code files

Available tools:
- execute_command: Run shell commands (requires user approval)
- read_file: Read log files or config files

Best practices:
1. Use safe, non-destructive commands when possible
2. Read error output carefully before retrying
3. Report exit codes and key output lines
4. Avoid commands that delete or overwrite important files
5. Prefer dry-run flags when available
"""
