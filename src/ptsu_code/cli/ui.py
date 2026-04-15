"""Rich UIコンポーネント。"""

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from ptsu_code.agent.sub_agents.base import AgentRole

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
        role: メッセージの役割
        content: メッセージ内容
    """
    if role == "user":
        prefix = "[bold cyan]You:[/bold cyan]"
    elif role == "assistant":
        prefix = "[bold green]Assistant:[/bold green]"
    elif role == "system":
        prefix = "[bold yellow]System:[/bold yellow]"
    else:
        prefix = content
        content = ""

    if content:
        console.print(f"{prefix} {content}")
    else:
        console.print(prefix)


def show_streaming_start(role: str = "assistant") -> None:
    """ストリーミング開始時のプレフィックスを表示する。

    Args:
        role: メッセージの役割
    """
    if role == "assistant":
        prefix = "[bold green]Assistant:[/bold green]"
    else:
        prefix = f"[bold]{role}:[/bold]"

    console.print(prefix, end=" ")


def show_streaming_chunk(content: str) -> None:
    """ストリーミングチャンクを表示する。

    Args:
        content: チャンク内容
    """
    console.print(content, end="")


def show_streaming_end() -> None:
    """ストリーミング終了時に改行する。"""
    console.print()


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


def show_tool_execution(tool_name: str, args: dict) -> None:
    """ツール実行中の表示。

    Args:
        tool_name: ツール名
        args: ツールの引数
    """
    # 引数を簡潔に表示
    args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    if len(args_str) > 100:
        args_str = args_str[:97] + "..."

    console.print(f"[dim]⚡ Executing:[/dim] [yellow]{tool_name}[/yellow]([dim]{args_str}[/dim])")


def show_tool_result(tool_name: str, success: bool, output: str = "", error: str = "") -> None:
    """ツール実行結果の表示。

    Args:
        tool_name: ツール名
        success: 成功したか
        output: 出力（成功時）
        error: エラーメッセージ（失敗時）
    """
    if success:
        # 出力を簡潔に表示
        output_preview = output.strip()
        if len(output_preview) > 100:
            lines = output_preview.split("\n")
            if len(lines) > 3:
                output_preview = "\n".join(lines[:3]) + f"\n... ({len(lines)} lines total)"
            else:
                output_preview = output_preview[:97] + "..."

        console.print(f"[dim]✓[/dim] [green]{tool_name}[/green]: {output_preview if output_preview else 'Success'}")
    else:
        error_preview = error[:100] if error else "Unknown error"
        console.print(f"[dim]✗[/dim] [red]{tool_name}[/red]: {error_preview}")


def show_coordinator_dispatch(role: AgentRole, agent_name: str, intent_label: str = "") -> None:
    """Coordinatorのディスパッチ情報を表示する。

    Args:
        role: 選択されたAgentRole
        agent_name: Sub-agentの名前
        intent_label: 意図ラベル（オプション）
    """
    role_styles = {
        AgentRole.SEARCHER: "cyan",
        AgentRole.CODER: "green",
        AgentRole.EXECUTOR: "yellow",
        AgentRole.GENERAL: "blue",
    }
    color = role_styles.get(role, "white")
    label = f" ({intent_label})" if intent_label else ""
    console.print(f"[bold {color}][{agent_name}][/bold {color}]{label} dispatched")


def show_tool_approval_request(tool_name: str, args: dict) -> str:
    """ツール実行の承認を求める。

    Args:
        tool_name: ツール名
        args: ツールの引数

    Returns:
        ユーザーの入力 ('y', 'n', 'a')
    """
    from rich.markup import escape
    from rich.table import Table

    # 引数を見やすく整形
    args_table = Table(show_header=False, box=None, padding=(0, 1))
    for key, value in args.items():
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:97] + "..."
        args_table.add_row(f"[bold]{escape(key)}[/bold]:", escape(value_str))

    panel = Panel(
        Group(
            Text.assemble(("Tool: ", "bold"), (tool_name, "yellow bold")),
            args_table,
            Text("[Y]es / [N]o / [A]lways approve this tool", style="dim"),
        ),
        title="[bold red]⚠ Tool Approval Required[/bold red]",
        border_style="yellow",
    )

    console.print(panel)
    console.print()

    while True:
        response = console.input("[bold]Your choice[/bold] ([yellow]y[/yellow]/[red]n[/red]/[green]a[/green]): ").lower().strip()
        if response in ("y", "yes"):
            return "y"
        elif response in ("n", "no"):
            return "n"
        elif response in ("a", "always"):
            return "a"
        else:
            console.print("[red]Invalid input. Please enter y, n, or a.[/red]")
