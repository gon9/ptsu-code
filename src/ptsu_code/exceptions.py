"""例外定義とエラーハンドリング。"""

from typing import Any


class PTSUError(Exception):
    """PTSU基底例外クラス。"""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """初期化。

        Args:
            message: エラーメッセージ
            details: エラー詳細情報
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(PTSUError):
    """設定エラー。"""


class InputError(PTSUError):
    """入力エラー。"""


class CommandExecutionError(PTSUError):
    """コマンド実行エラー。"""


def handle_exception(exc: Exception, verbose: bool = False) -> str:
    """例外を処理してユーザーフレンドリーなメッセージを返す。

    Args:
        exc: 例外オブジェクト
        verbose: 詳細情報を含めるかどうか

    Returns:
        エラーメッセージ
    """
    if isinstance(exc, PTSUError):
        msg = exc.message
        if verbose and exc.details:
            details_str = ", ".join(f"{k}={v}" for k, v in exc.details.items())
            msg = f"{msg} ({details_str})"
        return msg

    if isinstance(exc, KeyboardInterrupt):
        return "Operation cancelled by user"

    if isinstance(exc, EOFError):
        return "End of input reached"

    if verbose:
        return f"Unexpected error: {type(exc).__name__}: {exc}"

    return "An unexpected error occurred. Use --verbose for details."
