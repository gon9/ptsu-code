"""CLIアプリケーションのメインエントリーポイント。"""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from ptsu_code import __version__
from ptsu_code.agent.coordinator import Coordinator
from ptsu_code.agent.intent import IntentClassifier
from ptsu_code.agent.prompts import SystemPrompts
from ptsu_code.agent.providers.ollama_provider import OllamaProvider
from ptsu_code.agent.providers.probe import AvailableProviders, probe_providers
from ptsu_code.agent.runtime import AgentRuntime, AgentSession
from ptsu_code.agent.sub_agents.base import AgentRole
from ptsu_code.agent.sub_agents.coder import CoderAgent
from ptsu_code.agent.sub_agents.executor import ExecutorAgent
from ptsu_code.agent.sub_agents.searcher import SearcherAgent
from ptsu_code.agent.sub_agents.ultraplan import UltraPlanAgent
from ptsu_code.agent.tools.command_tool import CommandExecutionTool
from ptsu_code.agent.tools.file_tools import FileReadTool, FileWriteTool
from ptsu_code.agent.tools.memory_tools import MemorySummaryTool
from ptsu_code.agent.tools.plan_tools import ExitPlanModeTool, WritePlanTool
from ptsu_code.agent.tools.schedule_tools import (
    ScheduleCreateTool,
    ScheduleDeleteTool,
    ScheduleListTool,
)
from ptsu_code.agent.tools.search_tools import FindTool, GrepTool, ListDirTool
from ptsu_code.cli.prompt import UserPrompt
from ptsu_code.cli.ui import (
    show_coordinator_dispatch,
    show_error,
    show_info,
    show_message,
    show_provider_availability,
    show_schedule_fired,
    show_streaming_chunk,
    show_streaming_end,
    show_streaming_start,
    show_tool_approval_request,
    show_tool_execution,
    show_tool_result,
    show_ultraplan_progress,
    show_welcome,
)
from ptsu_code.config import settings
from ptsu_code.eval.logger import EvalLogger
from ptsu_code.exceptions import handle_exception
from ptsu_code.memory import SessionMemoryManager
from ptsu_code.scheduler import IdleTracker, SchedulerDaemon, ScheduleStore

app = typer.Typer(
    name="ptsu",
    help="PTSU - AI Agent CLI tool",
    add_completion=False,
)


def _build_coordinator(runtime: AgentRuntime) -> Coordinator:
    """Coordinatorインスタンスを構築する。

    Args:
        runtime: AgentRuntimeインスタンス

    Returns:
        Coordinatorインスタンス
    """
    classifier = IntentClassifier(runtime.provider)
    agents = {
        AgentRole.SEARCHER: SearcherAgent(),
        AgentRole.CODER: CoderAgent(),
        AgentRole.EXECUTOR: ExecutorAgent(),
        AgentRole.GENERAL: SearcherAgent(),
        AgentRole.ULTRAPLAN: UltraPlanAgent(),
    }
    return Coordinator(runtime=runtime, classifier=classifier, agents=agents)


@app.command()
def chat(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
    llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Enable LLM mode")] = True,
    provider: Annotated[str, typer.Option(help="LLM provider (openai, anthropic, or ollama)")] = "openai",
    stream: Annotated[bool, typer.Option("--stream/--no-stream", help="Enable streaming responses")] = True,
    coordinator: Annotated[bool, typer.Option("--coordinator/--no-coordinator", help="Enable Coordinator Mode")] = False,
    local_memory: Annotated[bool, typer.Option("--local-memory/--no-local-memory", help="Use local Ollama for memory extraction")] = False,
) -> None:
    """対話モードを起動する。"""
    try:
        if verbose:
            settings.verbose = verbose

        show_welcome(__version__)

        history_file = settings.history_dir / "chat_history.txt"
        prompt = UserPrompt(history_file=history_file)

        runtime = None
        session = None
        scheduler: SchedulerDaemon | None = None
        idle_tracker: IdleTracker | None = None
        memory_manager: SessionMemoryManager | None = None
        use_llm = llm

        # 起動時プロバイダー可用性チェック
        availability: AvailableProviders | None = None
        if use_llm:
            availability = probe_providers()
            show_provider_availability(availability)

        if use_llm:
            provider_name = provider or settings.llm_provider

            if not availability.is_available(provider_name):
                show_error(f"Provider '{provider_name}' is not available in this session.")
                show_info("Falling back to echo mode. Use --no-llm to suppress this message.")
                use_llm = False

            if use_llm:
                eval_logger = EvalLogger()
                runtime = AgentRuntime(provider=provider_name, eval_logger=eval_logger)
                session = AgentSession()
                schedule_store = ScheduleStore()
                session.tool_registry.register(FileReadTool())
                session.tool_registry.register(FileWriteTool())
                session.tool_registry.register(CommandExecutionTool())
                session.tool_registry.register(GrepTool())
                session.tool_registry.register(FindTool())
                session.tool_registry.register(ListDirTool())
                session.tool_registry.register(WritePlanTool())
                session.tool_registry.register(ExitPlanModeTool())
                session.tool_registry.register(ScheduleCreateTool(schedule_store))
                session.tool_registry.register(ScheduleListTool(schedule_store))
                session.tool_registry.register(ScheduleDeleteTool(schedule_store))

                session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                if local_memory and availability and not availability.is_available("ollama"):
                    show_info("Ollama not available — memory extraction falls back to main provider.")
                    local_memory = False

                memory_provider = (
                    OllamaProvider(
                        base_url=settings.ollama_base_url,
                        default_model=settings.ollama_model_fast,
                    )
                    if local_memory
                    else runtime.provider
                )
                if local_memory:
                    show_info(f"Memory extraction: Ollama ({settings.ollama_model_fast} @ {settings.ollama_base_url})")
                memory_manager = SessionMemoryManager(
                    provider=memory_provider,
                    session_id=session_id,
                    data_dir=Path.home() / ".ptsu",
                )
                session.tool_registry.register(MemorySummaryTool(memory_manager))
                runtime.session_tool_registry = session.tool_registry

                system_prompt = SystemPrompts.coding_assistant()
                prev_memory = memory_manager.load_previous()
                if prev_memory:
                    system_prompt += f"\n\n## Previous Session Memory\n{prev_memory}"
                    show_info("Previous session memory loaded.")
                session.add_message("system", system_prompt)
                runtime.start_eval_session(session_id)
                show_info(f"LLM mode enabled ({provider_name}) with {len(session.tool_registry)} tools available.")

                # スケジューラデーモンを起動
                idle_tracker = IdleTracker()
                scheduler = SchedulerDaemon(schedule_store, idle_tracker)
                scheduler.start()
                if schedule_store.count() > 0:
                    show_info(f"Scheduler started with {schedule_store.count()} persisted task(s).")

        show_info("Chat mode started. Type your message and press Enter.")

        pending_scheduled: list[tuple[str, str]] = []

        while True:
            # スケジューラから発火イベントをドレイン (idle前に集める)
            if scheduler is not None:
                _drain_scheduler(scheduler, pending_scheduled)

            # 発火済みタスクがあれば優先的に処理
            user_input: str | None
            if pending_scheduled:
                task_id, scheduled_prompt = pending_scheduled.pop(0)
                show_schedule_fired(task_id, scheduled_prompt)
                user_input = scheduled_prompt
            else:
                if idle_tracker is not None:
                    idle_tracker.set_idle(True)
                user_input = prompt.get_input("You > ")
                if idle_tracker is not None:
                    idle_tracker.set_idle(False)

            if user_input is None:
                show_info("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                show_info("Goodbye!")
                break

            if user_input.lower() == "/summary":
                if memory_manager:
                    ok = memory_manager.force_extract()
                    if ok:
                        show_info(f"Session memory saved: {memory_manager.storage.current_path}")
                    else:
                        show_info("No conversation to summarize yet.")
                else:
                    show_info("Session memory is not available in echo mode.")
                continue

            if user_input.lower() == "help":
                help_text = (
                    "Available commands:\n"
                    "  - exit, quit: Exit the chat\n"
                    "  - /summary: Save session memory now\n"
                    "  - help: Show this help message\n"
                )
                if use_llm and session:
                    help_text += f"  - LLM mode: Active with {len(session.tool_registry)} tools\n"
                    help_text += "  - Tools: read_file, write_file, execute_command, grep_search, find_files, list_directory"
                else:
                    help_text += "  - Echo mode: Messages are echoed back"
                show_message("system", help_text)
                continue

            if use_llm and runtime and session:
                try:
                    # 承認コールバック関数
                    def request_approval(tool_name: str, args: dict) -> str:
                        return show_tool_approval_request(tool_name, args)

                    # 進捗表示コールバック関数
                    def show_progress(tool_name: str, args: dict, status: str, **kwargs) -> None:
                        if status == "thinking":
                            show_ultraplan_progress(
                                args.get("turn", 0),
                                args.get("elapsed", 0),
                            )
                        elif status == "executing":
                            show_tool_execution(tool_name, args)
                        elif status == "completed":
                            show_tool_result(
                                tool_name,
                                kwargs.get("success", False),
                                kwargs.get("output", ""),
                                kwargs.get("error", ""),
                            )

                    # ストリーミングコールバック関数
                    def handle_stream(event: str, content: str = "") -> None:
                        if event == "start":
                            show_streaming_start()
                        elif event == "chunk":
                            show_streaming_chunk(content)
                        elif event == "end":
                            show_streaming_end()

                    msg_count_before = len(session.messages) if session else 0
                    if coordinator:
                        coord = _build_coordinator(runtime)
                        response = coord.process(
                            user_input,
                            on_dispatch=show_coordinator_dispatch,
                            request_approval_callback=request_approval,
                            show_progress_callback=show_progress,
                        )
                        show_message("assistant", response)
                        if memory_manager:
                            memory_manager.add_turn(user_input, response)
                            memory_manager.maybe_extract()
                    elif stream:
                        response = runtime.run_loop_stream(
                            session, user_input, request_approval, show_progress, handle_stream
                        )
                        if memory_manager and session:
                            tool_count = _count_new_tool_calls(session, msg_count_before)
                            memory_manager.add_turn(user_input, response, tool_count)
                            memory_manager.maybe_extract()
                    else:
                        response = runtime.run_loop(session, user_input, request_approval, show_progress)
                        show_message("assistant", response)
                        if memory_manager and session:
                            tool_count = _count_new_tool_calls(session, msg_count_before)
                            memory_manager.add_turn(user_input, response, tool_count)
                            memory_manager.maybe_extract()
                except Exception as e:
                    error_msg = handle_exception(e, verbose=settings.verbose)
                    show_error(f"LLM error: {error_msg}")
                    if settings.verbose:
                        import traceback

                        show_error(traceback.format_exc())
            else:
                show_message("assistant", f"Echo: {user_input}")

    except Exception as e:
        error_msg = handle_exception(e, verbose=settings.verbose)
        show_error(error_msg)
        raise typer.Exit(code=1) from e
    finally:
        if memory_manager is not None:
            try:
                memory_manager.finalize()
            except Exception:
                pass
        if runtime is not None:
            try:
                runtime.finalize_eval_session()
            except Exception:
                pass
        if scheduler is not None:
            scheduler.stop()


def _count_new_tool_calls(session: AgentSession, msg_count_before: int) -> int:
    """指定のメッセージインデックス以降のツール呼び出し数を返す。

    Args:
        session: エージェントセッション
        msg_count_before: ターン開始前のメッセージ数

    Returns:
        ツール呼び出し数
    """
    new_msgs = session.messages[msg_count_before:]
    return sum(
        len(msg.tool_calls)
        for msg in new_msgs
        if msg.role == "assistant" and msg.tool_calls
    )


def _drain_scheduler(
    scheduler: SchedulerDaemon,
    pending: list[tuple[str, str]],
) -> None:
    """スケジューラの fire_queue を pending リストへ移し替える。

    Args:
        scheduler: スケジューラデーモン
        pending: 保留中の (task_id, prompt) ペアリスト (mutated)
    """
    while True:
        try:
            event = scheduler.fire_queue.get_nowait()
        except Exception:
            break
        pending.append((event.task_id, event.prompt))


@app.command()
def version() -> None:
    """バージョン情報を表示する。"""
    typer.echo(f"PTSU version {__version__}")


def main() -> None:
    """メインエントリーポイント。"""
    app()


if __name__ == "__main__":
    main()
