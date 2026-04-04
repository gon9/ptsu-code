"""例外ハンドリングのテスト。"""

import pytest

from ptsu_code.exceptions import (
    CommandExecutionError,
    ConfigurationError,
    InputError,
    PTSUError,
    handle_exception,
)


class TestPTSUError:
    """PTSU例外クラスのテスト。"""

    @pytest.mark.parametrize(
        ("exception_class", "message", "details"),
        [
            (PTSUError, "Base error", {"key": "value"}),
            (ConfigurationError, "Config error", None),
            (InputError, "Input error", {"input": "invalid"}),
            (CommandExecutionError, "Command failed", {"cmd": "test"}),
        ],
    )
    def test_exception_creation(self, exception_class, message, details):
        """例外が正しく生成されることを確認する。"""
        exc = exception_class(message, details)
        assert exc.message == message
        assert exc.details == (details or {})
        assert str(exc) == message


class TestHandleException:
    """handle_exception関数のテスト。"""

    @pytest.mark.parametrize(
        ("exception", "verbose", "expected_contains"),
        [
            (PTSUError("Test error"), False, "Test error"),
            (PTSUError("Test error", {"key": "value"}), True, "key=value"),
            (ConfigurationError("Config error"), False, "Config error"),
            (KeyboardInterrupt(), False, "cancelled by user"),
            (EOFError(), False, "End of input"),
            (ValueError("Some error"), False, "unexpected error occurred"),
            (ValueError("Some error"), True, "ValueError: Some error"),
        ],
    )
    def test_handle_exception_messages(self, exception, verbose, expected_contains):
        """例外処理が正しいメッセージを返すことを確認する。"""
        result = handle_exception(exception, verbose=verbose)
        assert expected_contains in result

    def test_handle_exception_ptsu_error_with_details(self):
        """PTSU例外の詳細情報が正しく処理されることを確認する。"""
        exc = PTSUError("Error message", {"detail1": "value1", "detail2": "value2"})
        result = handle_exception(exc, verbose=True)
        assert "Error message" in result
        assert "detail1=value1" in result
        assert "detail2=value2" in result

    def test_handle_exception_ptsu_error_without_verbose(self):
        """verboseがFalseの場合、詳細情報が含まれないことを確認する。"""
        exc = PTSUError("Error message", {"detail": "value"})
        result = handle_exception(exc, verbose=False)
        assert result == "Error message"
        assert "detail" not in result
