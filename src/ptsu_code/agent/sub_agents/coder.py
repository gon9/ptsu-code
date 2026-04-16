"""コード生成・編集に特化したSub-agent。"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent, SubAgentConfig
from ptsu_code.config import get_model

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime


class CoderAgent(SubAgent):
    """コード生成・編集を担当するSub-agent。

    read_file / write_file を使い、既存コードを理解した上で修正・新規作成を行う。
    write_file は承認フロー付きで安全に実行される。
    """

    @property
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""
        return SubAgentConfig(
            role=AgentRole.CODER,
            name="Coder",
            description="Reads and writes code files to implement features or fix bugs",
            system_prompt=self._get_system_prompt(),
            allowed_tools=["read_file", "write_file", "grep_search", "find_files", "list_directory"],
            max_turns=10,
            temperature=None,
            provider="anthropic",
            model_tier="smart",
        )

    def run(
        self,
        runtime: "AgentRuntime",
        message: str,
        context: dict[str, Any] | None = None,
        request_approval_callback: Callable | None = None,
        show_progress_callback: Callable | None = None,
    ) -> str:
        """コード生成・編集タスクを実行する。

        Args:
            runtime: AgentRuntimeインスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）
            request_approval_callback: ツール承認コールバック（オプション）
            show_progress_callback: 進捗表示コールバック（オプション）

        Returns:
            実行結果
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
            context_lines = [f"{k}: {v}" for k, v in context.items()]
            session.add_message("system", "Context:\n" + "\n".join(context_lines))

        return agent_runtime.run_loop(session, message, request_approval_callback, show_progress_callback)

    def _get_system_prompt(self) -> str:
        """システムプロンプトを返す。"""
        return """You are a Coder Agent specialized in reading and writing code.

Your role:
- Read existing code to understand context before making changes
- Write or modify files to implement features or fix bugs
- Verify your changes by reading the modified files
- Keep changes minimal and focused

Available tools:
- read_file: Read file contents (ALWAYS read before writing)
- write_file: Write or modify files
- grep_search: Search for patterns in files
- find_files: Find files by name
- list_directory: List directory contents

IMPORTANT: Call write_file directly without asking for permission. The system handles approval automatically — you do NOT need to ask the user.

Best practices:
1. Always read the target file before modifying it
2. Make minimal, focused changes
3. Preserve existing code style and conventions
4. Verify changes after writing
5. Explain what you changed and why
"""
