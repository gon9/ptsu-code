"""CLIアプリケーションのメインエントリーポイント。"""

from typing import Annotated

import typer

from ptsu_code import __version__
from ptsu_code.cli.prompt import UserPrompt
from ptsu_code.cli.ui import show_error, show_info, show_message, show_welcome
from ptsu_code.config import settings
from ptsu_code.exceptions import handle_exception

app = typer.Typer(
    name="ptsu",
    help="PTSU - Claude Code Clone with unreleased features",
    add_completion=False,
)


@app.command()
def chat(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """対話モードを起動する。"""
    try:
        if verbose:
            settings.verbose = verbose

        show_welcome(__version__)

        history_file = settings.history_dir / "chat_history.txt"
        prompt = UserPrompt(history_file=history_file)

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
                show_message(
                    "system",
                    "Available commands:\n"
                    "  - exit, quit: Exit the chat\n"
                    "  - help: Show this help message\n"
                    "  - Any other text: Echo back (LLM integration coming in Day 3)",
                )
                continue

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
