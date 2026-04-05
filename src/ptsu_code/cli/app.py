"""CLIアプリケーションのメインエントリーポイント。"""

from typing import Annotated

import typer

from ptsu_code import __version__
from ptsu_code.agent.runtime import AgentRuntime, AgentSession
from ptsu_code.agent.tools.command_tool import CommandExecutionTool
from ptsu_code.agent.tools.file_tools import FileReadTool, FileWriteTool
from ptsu_code.agent.tools.search_tools import FindTool, GrepTool, ListDirTool
from ptsu_code.cli.prompt import UserPrompt
from ptsu_code.cli.ui import (
    show_error,
    show_info,
    show_message,
    show_tool_approval_request,
    show_tool_execution,
    show_tool_result,
    show_welcome,
)
from ptsu_code.config import settings
from ptsu_code.exceptions import handle_exception

app = typer.Typer(
    name="ptsu",
    help="PTSU - AI Agent CLI tool",
    add_completion=False,
)


@app.command()
def chat(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
    use_llm: Annotated[bool, typer.Option("--llm/--no-llm", help="Use LLM (requires API key)")] = True,
    provider: Annotated[str, typer.Option("--provider", "-p", help="LLM provider (openai/anthropic)")] = "",
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

        if use_llm:
            provider_name = provider or settings.llm_provider

            # APIキーチェック
            if provider_name == "anthropic":
                if not settings.anthropic_api_key:
                    show_error("Anthropic API key is not configured. Set PTSU_ANTHROPIC_API_KEY environment variable.")
                    show_info("Falling back to echo mode. Use --no-llm to suppress this message.")
                    use_llm = False
            else:
                if not settings.openai_api_key:
                    show_error("OpenAI API key is not configured. Set PTSU_OPENAI_API_KEY environment variable.")
                    show_info("Falling back to echo mode. Use --no-llm to suppress this message.")
                    use_llm = False

            if use_llm:
                runtime = AgentRuntime(provider=provider_name)
                session = AgentSession()
                session.tool_registry.register(FileReadTool())
                session.tool_registry.register(FileWriteTool())
                session.tool_registry.register(CommandExecutionTool())
                session.tool_registry.register(GrepTool())
                session.tool_registry.register(FindTool())
                session.tool_registry.register(ListDirTool())

                system_prompt = (
                    "You are PTSU, an AI coding assistant. You have access to tools for file operations "
                    "and command execution. Help the user with their coding tasks efficiently."
                )
                session.add_message("system", system_prompt)
                show_info(f"LLM mode enabled ({provider_name}) with {len(session.tool_registry)} tools available.")

        show_info("Chat mode started. Type your message and press Enter.")

        while True:
            user_input = prompt.get_input("You > ")

            if user_input is None:
                show_info("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                show_info("Goodbye!")
                break

            if user_input.lower() == "help":
                help_text = (
                    "Available commands:\n"
                    "  - exit, quit: Exit the chat\n"
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
                        if status == "executing":
                            show_tool_execution(tool_name, args)
                        elif status == "completed":
                            show_tool_result(
                                tool_name,
                                kwargs.get("success", False),
                                kwargs.get("output", ""),
                                kwargs.get("error", ""),
                            )

                    response = runtime.run_loop(session, user_input, request_approval, show_progress)
                    show_message("assistant", response)
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


@app.command()
def version() -> None:
    """バージョン情報を表示する。"""
    typer.echo(f"PTSU version {__version__}")


def main() -> None:
    """メインエントリーポイント。"""
    app()


if __name__ == "__main__":
    main()
