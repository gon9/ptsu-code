"""コードベース調査・検索に特化したSub-agent。"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent, SubAgentConfig
from ptsu_code.config import get_model

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime


class SearcherAgent(SubAgent):
    """コードベースの調査・検索を担当するSub-agent。

    読み取り専用ツールのみ使用し、ファイル書き込みやコマンド実行は行わない。
    """

    @property
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""
        return SubAgentConfig(
            role=AgentRole.SEARCHER,
            name="Searcher",
            description="Explores and searches the codebase to find relevant files and code sections",
            system_prompt=self._get_system_prompt(),
            allowed_tools=[
                "read_file",
                "grep_search",
                "find_files",
                "list_directory",
                "schedule_create",
                "schedule_list",
                "schedule_delete",
            ],
            max_turns=10,
            temperature=None,
            provider="openai",
            model_tier="fast",
        )

    def run(
        self,
        runtime: "AgentRuntime",
        message: str,
        context: dict[str, Any] | None = None,
        request_approval_callback: Callable | None = None,
        show_progress_callback: Callable | None = None,
    ) -> str:
        """コードベース検索タスクを実行する。

        allowed_toolsのみをセッションに登録してruntime.run_loopを呼び出す。

        Args:
            runtime: AgentRuntimeインスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）

        Returns:
            検索結果のサマリー
        """
        from ptsu_code.agent.runtime import AgentSession
        from ptsu_code.agent.tools.registry import ToolRegistry

        cfg = self.config
        agent_runtime = self._get_runtime(runtime)

        restricted_registry = ToolRegistry()
        for tool_name in cfg.allowed_tools:
            tool = runtime.session_tool_registry.get(tool_name) if hasattr(runtime, "session_tool_registry") else None
            if tool is not None:
                restricted_registry.register(tool)

        session = AgentSession(
            tool_registry=restricted_registry,
            model=get_model(agent_runtime.provider_name, cfg.model_tier),
            max_turns=cfg.max_turns,
            temperature=cfg.temperature,
        )
        session.add_message("system", cfg.system_prompt)

        if context:
            context_lines = []
            for key, value in context.items():
                context_lines.append(f"{key}: {value}")
            context_text = "\n".join(context_lines)
            session.add_message("system", f"Context:\n{context_text}")

        return agent_runtime.run_loop(session, message, request_approval_callback, show_progress_callback)

    def _get_system_prompt(self) -> str:
        """システムプロンプトを返す。"""
        return """You are a Searcher Agent specialized in exploring codebases.

Your role:
- Find relevant files and code sections
- Understand code structure and dependencies
- Provide clear summaries of findings
- DO NOT modify any files

IMPORTANT: If file output is truncated, summarize what you have received. Do NOT re-read the same file multiple times — read each file once and move on.
- DO NOT execute any commands

Available tools:
- read_file: Read file contents
- grep_search: Search for patterns in files
- find_files: Find files by name
- list_directory: List directory contents
- schedule_create / schedule_list / schedule_delete: Manage scheduled prompts that fire
  at a cron-specified time inside the running ptsu REPL. Call these tools DIRECTLY for
  scheduling/reminder/timer requests. NEVER write a script file to create schedules.

Scheduling requests (e.g. "1分後に X して", "毎日9時に Y を実行", "予定一覧を教えて"):
- Translate the time into a 5-field cron expression (M H DoM Mon DoW) in LOCAL time
- recurring=false for one-shot ("1分後", "明日の朝"); recurring=true for repeating
- durable=true only if the user asks to survive ptsu restarts
- For "list my schedules" → call schedule_list; for "cancel X" → schedule_delete

Best practices:
1. Start with broad searches (grep, find)
2. Read relevant files to understand context
3. Provide structured summaries
4. Include file paths and line numbers in your findings
"""
