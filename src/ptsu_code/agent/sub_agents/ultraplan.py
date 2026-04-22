"""ULTRAPLANモードのSub-agent。"""

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ptsu_code.agent.sub_agents.base import AgentRole, SubAgent, SubAgentConfig
from ptsu_code.agent.tools.plan_tools import ExitPlanModeTool, WritePlanTool
from ptsu_code.config import get_model

if TYPE_CHECKING:
    from ptsu_code.agent.runtime import AgentRuntime, AgentSession

_ULTRAPLAN_MAX_TURNS = 30
_ULTRAPLAN_THINKING_BUDGET = 10_000
_RATE_LIMIT_RETRIES = 4
_RATE_LIMIT_BASE_WAIT = 15


class UltraPlanAgent(SubAgent):
    """長時間思考・多段階調査を行うULTRAPLANモードのSub-agent。

    claude-code-mainのULTRAPLAN機構をローカルで再現する。
    通常のmax_turnsによる終了ではなく、LLMがexit_plan_modeツールを
    呼び出してユーザーが承認した時点でループを終了する。

    動作フロー:
    1. read_file / grep_search / find_files で調査フェーズ
    2. write_plan で計画をファイルへ保存
    3. exit_plan_mode でユーザーに承認を求める
    4. 承認 → approved_plan を返して終了
    5. 却下 → フィードバック付きで調査・計画を継続
    """

    @property
    def config(self) -> SubAgentConfig:
        """Sub-agentの設定を返す。"""
        return SubAgentConfig(
            role=AgentRole.ULTRAPLAN,
            name="UltraPlan",
            description=(
                "Deep investigation and multi-phase planning. "
                "Uses extended thinking to analyze the codebase and produce a detailed plan."
            ),
            system_prompt=self._get_system_prompt(),
            allowed_tools=[
                "read_file",
                "grep_search",
                "find_files",
                "list_directory",
                "write_plan",
                "exit_plan_mode",
            ],
            max_turns=_ULTRAPLAN_MAX_TURNS,
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
        """ULTRAPLANモードでタスクを実行する。

        run_loop()を使わず、exit_plan_modeの承認を検出するカスタムループを実装する。

        Args:
            runtime: AgentRuntimeインスタンス
            message: ユーザーメッセージ
            context: コンテキスト情報（オプション）
            request_approval_callback: ツール承認コールバック（オプション）
            show_progress_callback: 進捗表示コールバック（オプション）

        Returns:
            承認されたプラン内容、またはフォールバックの応答
        """
        from ptsu_code.agent.runtime import AgentSession
        from ptsu_code.agent.tools.registry import ToolRegistry

        cfg = self.config
        agent_runtime = self._get_runtime(runtime)

        exit_tool = ExitPlanModeTool()
        write_tool = WritePlanTool()

        restricted_registry = ToolRegistry()
        for tool_name in cfg.allowed_tools:
            if tool_name == "exit_plan_mode":
                restricted_registry.register(exit_tool)
            elif tool_name == "write_plan":
                restricted_registry.register(write_tool)
            else:
                tool = (
                    runtime.session_tool_registry.get(tool_name)
                    if hasattr(runtime, "session_tool_registry")
                    else None
                )
                if tool is not None:
                    restricted_registry.register(tool)

        thinking_budget = (
            _ULTRAPLAN_THINKING_BUDGET
            if agent_runtime.provider_name == "anthropic"
            else None
        )

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

        session.add_message("user", message)
        start_time = time.time()

        for turn in range(cfg.max_turns):
            elapsed = int(time.time() - start_time)
            if show_progress_callback:
                show_progress_callback(
                    "ultraplan",
                    {"turn": turn + 1, "elapsed": elapsed},
                    "thinking",
                )

            scaled_budget = self._scale_thinking_budget(thinking_budget, turn, cfg.max_turns)
            response = self._run_turn_with_thinking(agent_runtime, session, scaled_budget)

            if response.tool_calls:
                session.add_message(
                    "assistant",
                    response.content,
                    tool_calls=response.tool_calls,
                )
                tool_results = agent_runtime.execute_tool_calls(
                    session,
                    response.tool_calls,
                    request_approval_callback,
                    show_progress_callback,
                )
                for result in tool_results:
                    session.messages.append(result)

                if exit_tool.plan_approved and exit_tool.approved_plan:
                    return exit_tool.approved_plan

            else:
                session.add_message("assistant", response.content)
                if "ULTRAPLAN_COMPLETE" in response.content and exit_tool.approved_plan:
                    return exit_tool.approved_plan
                if not response.tool_calls:
                    return response.content

        return f"ULTRAPLAN reached max turns ({cfg.max_turns}) without completing. Last state: planning in progress."

    def _scale_thinking_budget(
        self,
        base_budget: int | None,
        turn: int,
        max_turns: int,
    ) -> int | None:
        """ターン進行度に応じてthinking_budgetを段階的に削減する。

        調査フェーズ（前半）は深い思考が必要なため予算をフルに使い、
        計画作成・出力フェーズ（後半）は生成コストを抑えるため削減する。

        Args:
            base_budget: 基本thinking_budget（Noneの場合は変換なし）
            turn: 現在のターン番号（0始まり）
            max_turns: 最大ターン数

        Returns:
            スケール済みthinking_budget。後半はNone（無効化）
        """
        if base_budget is None or max_turns == 0:
            return base_budget

        ratio = turn / max_turns
        if ratio < 0.33:
            return base_budget
        if ratio < 0.67:
            return max(1024, base_budget // 2)
        return None

    def _run_turn_with_thinking(
        self,
        runtime: "AgentRuntime",
        session: "AgentSession",
        thinking_budget: int | None,
    ) -> Any:
        """Extended Thinkingオプション付きでターンを実行する。

        429 Rate Limit エラーは指数バックオフでリトライする。

        Args:
            runtime: AgentRuntimeインスタンス
            session: AgentSessionインスタンス
            thinking_budget: Extended Thinkingのトークン予算（Anthropicのみ）

        Returns:
            LLMレスポンス
        """
        from ptsu_code.agent.providers.anthropic_provider import AnthropicProvider
        from ptsu_code.agent.runtime import RuntimeError

        tools = (
            session.tool_registry.get_openai_schemas()
            if len(session.tool_registry) > 0
            else None
        )

        last_exc: Exception | None = None
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            try:
                if thinking_budget and isinstance(runtime.provider, AnthropicProvider):
                    return runtime.provider.chat(
                        messages=session.get_messages(),
                        tools=tools,
                        model=session.model,
                        thinking_budget=thinking_budget,
                    )
                return runtime.provider.chat(
                    messages=session.get_messages(),
                    tools=tools,
                    temperature=session.temperature,
                    model=session.model,
                )
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str:
                    if attempt < _RATE_LIMIT_RETRIES:
                        wait = _RATE_LIMIT_BASE_WAIT * (2**attempt)
                        time.sleep(wait)
                        last_exc = e
                        continue
                raise RuntimeError(
                    f"ULTRAPLAN turn failed: {e}",
                    {"provider": runtime.provider_name},
                ) from e

        raise RuntimeError(
            f"ULTRAPLAN rate limit: max retries exceeded: {last_exc}",
            {"provider": runtime.provider_name},
        ) from last_exc

    def _get_system_prompt(self) -> str:
        """ULTRAPLANモードのシステムプロンプトを返す。"""
        return """You are in ULTRAPLAN mode — a deep investigation and planning agent.

Your mission:
1. **ANALYZE**: Thoroughly explore the codebase using available tools
   - Read key files, search for patterns, understand architecture
   - Do NOT rush — take as many turns as needed to fully understand
2. **PLAN**: Write a detailed implementation plan using write_plan
   - Include: what to change, why, file-by-file breakdown, risks
   - Save to /tmp/ptsu-plan.md using the write_plan tool
3. **PRESENT**: Call exit_plan_mode when your plan is complete
   - Provide a clear 1-3 line summary for the user
   - The user will review and approve or reject your plan

Available tools:
- read_file: Read file contents (use offset/limit for large files)
- grep_search: Search for patterns across files
- find_files: Find files by name pattern
- list_directory: List directory contents
- write_plan: Save your Markdown plan to a file
- exit_plan_mode: Present plan for user approval (call this LAST)

IMPORTANT RULES:
- Always call exit_plan_mode when ready — never just output the plan as text
- Always call write_plan BEFORE exit_plan_mode
- If the user rejects your plan, refine it based on their feedback
- When the tool result says "ULTRAPLAN_COMPLETE", respond with exactly: ULTRAPLAN_COMPLETE
"""
