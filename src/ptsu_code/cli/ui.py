"""Rich UIコンポーネント。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def show_welcome(version: str) -> None:
    """ウェルカム画面を表示する。

    Args:
        version: アプリケーションバージョン
    """
    logo = Text.from_markup(
        "[bold cyan]PTSU[/bold cyan] - [italic]AI Agent CLI[/italic]",
        justify="center",
    )
    welcome_text = Text.from_markup(
        f"Version: [yellow]{version}[/yellow]\n"
        "Type [bold]'exit'[/bold] or [bold]'quit'[/bold] to exit, [bold]Ctrl+D[/bold] to quit\n"
        "Type [bold]'help'[/bold] for available commands",
        justify="center",
    )

    panel = Panel(
        Text.assemble(logo, "\n\n", welcome_text),
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_message(role: str, content: str) -> None:
    """メッセージを表示する。

    Args:
        role: メッセージの送信者 (user/assistant/system)
        content: メッセージ内容
    """
    if role == "user":
        console.print(f"[bold blue]You:[/bold blue] {content}")
    elif role == "assistant":
        console.print(f"[bold green]Assistant:[/bold green] {content}")
    elif role == "system":
        console.print(f"[bold yellow]System:[/bold yellow] {content}")
    else:
        console.print(content)


def show_error(message: str) -> None:
    """エラーメッセージを表示する。

    Args:
        message: エラーメッセージ
    """
    console.print(f"[bold red]Error:[/bold red] {message}")


def show_info(message: str) -> None:
    """情報メッセージを表示する。

    Args:
        message: 情報メッセージ
    """
    console.print(f"[cyan]ℹ[/cyan] {message}")
