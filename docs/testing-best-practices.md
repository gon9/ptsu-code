---
tags:
  - testing
  - best_practices
  - guidelines
aliases:
  - テストベストプラクティス
---

# テストベストプラクティス

## 概要

このプロジェクトで採用している効率的なテスト手法とパターンをまとめたドキュメント。
カバレッジ 80% 以上を維持しつつ、保守性の高いテストコードを書くための指針。

---

## 1. Exception Handler の集約パターン

### 原則

**全ての例外処理を一箇所に集約し、統一的なエラーハンドリングを実現する**

### 実装パターン

```python
# src/[package]/exceptions.py

class AppError(Exception):
    """基底例外クラス"""
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ConfigurationError(AppError):
    """設定エラー"""

class InputError(AppError):
    """入力エラー"""

def handle_exception(exc: Exception, verbose: bool = False) -> str:
    """例外を処理してユーザーフレンドリーなメッセージを返す"""
    if isinstance(exc, AppError):
        msg = exc.message
        if verbose and exc.details:
            details_str = ", ".join(f"{k}={v}" for k, v in exc.details.items())
            msg = f"{msg} ({details_str})"
        return msg
    
    if isinstance(exc, KeyboardInterrupt):
        return "Operation cancelled by user"
    
    if verbose:
        return f"Unexpected error: {type(exc).__name__}: {exc}"
    
    return "An unexpected error occurred. Use --verbose for details."
```

### メリット

- ✅ エラーメッセージの一貫性
- ✅ テストが容易（1箇所をテストすれば全体をカバー）
- ✅ 保守性が高い（変更箇所が明確）
- ✅ verbose モードでデバッグ情報を出力可能

### 使用例

```python
# アプリケーションコード
try:
    # 処理
    pass
except Exception as e:
    error_msg = handle_exception(e, verbose=settings.verbose)
    show_error(error_msg)
    raise typer.Exit(code=1) from e
```

---

## 2. Parametrized Testing（パラメータ化テスト）

### 原則

**正常系・異常系を含む複数のテストケースを1つのテスト関数で効率的にカバーする**

### 実装パターン

```python
import pytest

@pytest.mark.parametrize(
    ("input_value", "expected_output"),
    [
        ("hello", "hello"),           # 正常系
        ("  spaces  ", "spaces"),     # 正常系（トリム）
        ("", ""),                      # エッジケース（空文字列）
    ],
)
def test_process_input(input_value, expected_output):
    """入力処理が正しく動作することを確認する"""
    result = process_input(input_value)
    assert result == expected_output
```

### 異常系のパラメータ化

```python
@pytest.mark.parametrize(
    ("exception", "verbose", "expected_contains"),
    [
        (AppError("Test error"), False, "Test error"),
        (AppError("Error", {"key": "value"}), True, "key=value"),
        (KeyboardInterrupt(), False, "cancelled by user"),
        (ValueError("Some error"), False, "unexpected error"),
        (ValueError("Some error"), True, "ValueError: Some error"),
    ],
)
def test_handle_exception(exception, verbose, expected_contains):
    """例外処理が正しいメッセージを返すことを確認する"""
    result = handle_exception(exception, verbose=verbose)
    assert expected_contains in result
```

### メリット

- ✅ テストケースの追加が容易（タプルを追加するだけ）
- ✅ コードの重複を削減
- ✅ テストの意図が明確（パラメータ名で自己文書化）
- ✅ 失敗時にどのケースで失敗したか明確

---

## 3. テストクラスによる構造化

### 原則

**関連するテストをクラスでグループ化し、可読性と保守性を向上させる**

### 実装パターン

```python
class TestUserPrompt:
    """UserPromptクラスのテスト"""
    
    def test_init_without_history_file(self):
        """履歴ファイルなしで初期化できることを確認する"""
        prompt = UserPrompt()
        assert prompt.history_file is None
    
    def test_init_with_history_file(self, tmp_path):
        """履歴ファイルありで初期化できることを確認する"""
        history_file = tmp_path / "history.txt"
        prompt = UserPrompt(history_file=history_file)
        assert prompt.history_file == history_file
    
    @pytest.mark.parametrize(
        "exception",
        [EOFError, KeyboardInterrupt],
    )
    def test_get_input_interruption(self, exception):
        """中断時にNoneを返すことを確認する"""
        prompt = UserPrompt()
        with patch.object(prompt.session, "prompt", side_effect=exception):
            result = prompt.get_input("> ")
            assert result is None
```

### メリット

- ✅ テストの構造が明確
- ✅ 関連するテストが見つけやすい
- ✅ setup/teardown をクラスレベルで共有可能
- ✅ テストレポートが階層的で読みやすい

---

## 4. Mock と Patch の活用

### 原則

**外部依存を Mock で置き換え、テストの独立性と速度を確保する**

### 実装パターン

#### 関数のモック

```python
from unittest.mock import patch, MagicMock

def test_function_with_external_dependency(self):
    """外部依存を持つ関数のテスト"""
    with patch("module.external_function") as mock_func:
        mock_func.return_value = "mocked_value"
        
        result = function_under_test()
        
        mock_func.assert_called_once()
        assert result == "expected_result"
```

#### 例外発生のシミュレーション

```python
def test_error_handling(self):
    """例外発生時のエラーハンドリングを確認する"""
    with patch("module.UserPrompt") as mock_prompt:
        mock_instance = MagicMock()
        mock_instance.get_input.side_effect = AppError("Test error")
        mock_prompt.return_value = mock_instance
        
        result = runner.invoke(app, ["chat"])
        
        assert result.exit_code == 1
        assert "Test error" in result.stdout
```

### メリット

- ✅ 外部サービス（API、DB）に依存しない
- ✅ テストが高速
- ✅ エラーケースを簡単にシミュレート可能
- ✅ テストの再現性が高い

---

## 5. Fixture の活用

### 原則

**共通のセットアップ処理を Fixture として定義し、再利用性を高める**

### 実装パターン

```python
import pytest
from io import StringIO
from rich.console import Console

@pytest.fixture
def console_output():
    """コンソール出力をキャプチャするフィクスチャ"""
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True, width=120)
    return string_io, console

@pytest.fixture
def temp_config_file(tmp_path):
    """一時的な設定ファイルを作成するフィクスチャ"""
    config_file = tmp_path / "config.toml"
    config_file.write_text("[settings]\nverbose = true")
    return config_file

def test_with_fixture(console_output):
    """フィクスチャを使用したテスト"""
    string_io, console = console_output
    # テストコード
```

### メリット

- ✅ セットアップコードの重複を削減
- ✅ テストの可読性が向上
- ✅ 一時ファイル・ディレクトリの自動クリーンアップ
- ✅ テスト間の独立性を保証

---

## 6. テストカバレッジの目標

### 基準

- **最低ライン**: 80%
- **推奨**: 90% 以上
- **例外**: 以下は低カバレッジを許容
  - `__main__.py`: エントリーポイント（実行時のみ動作）
  - 対話ループの実行時パス（実際のユーザー入力が必要）

### カバレッジ確認コマンド

```bash
# カバレッジ付きでテスト実行
uv run pytest

# カバレッジレポートをHTML形式で出力
uv run pytest --cov-report=html

# 特定のモジュールのみカバレッジ確認
uv run pytest --cov=src/ptsu_code/cli
```

---

## 7. テストの命名規則

### 原則

**テスト名から「何をテストしているか」が明確にわかるようにする**

### パターン

```python
# ✅ Good: 動作が明確
def test_version_command_displays_correct_version():
    """versionコマンドが正しいバージョンを表示することを確認する"""
    pass

def test_chat_command_exits_on_quit_input():
    """quitコマンドで終了することを確認する"""
    pass

def test_handle_exception_returns_user_friendly_message():
    """例外処理がユーザーフレンドリーなメッセージを返すことを確認する"""
    pass

# ❌ Bad: 何をテストしているか不明確
def test_version():
    pass

def test_chat():
    pass

def test_exception():
    pass
```

### Docstring の記述

```python
def test_parametrized_input_processing(self, input_value, expected_output):
    """入力処理が正しく動作することを確認する。
    
    正常系、エッジケース（空文字列、スペース）を含む。
    """
    pass
```

---

## 8. テスト実行のベストプラクティス

### 開発時

```bash
# 全テスト実行（カバレッジ付き）
uv run pytest

# 特定のテストファイルのみ実行
uv run pytest tests/cli/test_app.py

# 特定のテストクラス・関数のみ実行
uv run pytest tests/cli/test_app.py::TestChatCommand::test_chat_command_exit

# 失敗したテストのみ再実行
uv run pytest --lf

# verbose モード
uv run pytest -v

# 簡潔な出力
uv run pytest -q
```

### CI/CD

```bash
# 全テスト + Lint + カバレッジチェック
uv run ruff check src/ tests/
uv run pytest --cov-fail-under=80
```

---

## 9. テストファイルの配置

### ディレクトリ構造

```
tests/
├── __init__.py
├── test_config.py              # トップレベルモジュールのテスト
├── test_exceptions.py
├── test_main.py
└── cli/                        # サブパッケージのテスト
    ├── __init__.py
    ├── test_app.py
    ├── test_prompt.py
    └── test_ui.py
```

### 原則

- ソースコードの構造とテストの構造を一致させる
- `src/ptsu_code/cli/app.py` → `tests/cli/test_app.py`
- 1モジュール = 1テストファイル

---

## 10. アンチパターン（避けるべきこと）

### ❌ テストの相互依存

```python
# Bad: テストの実行順序に依存
class TestBad:
    shared_state = None
    
    def test_step1(self):
        self.shared_state = "value"
    
    def test_step2(self):
        assert self.shared_state == "value"  # test_step1 に依存
```

### ❌ 過度なモック

```python
# Bad: 全てをモックしてテストの意味がない
def test_over_mocked(self):
    with patch("module.function_a"), \
         patch("module.function_b"), \
         patch("module.function_c"):
        # 実際には何もテストしていない
        pass
```

### ❌ 曖昧なアサーション

```python
# Bad: 何を確認しているか不明確
def test_bad_assertion(self):
    result = some_function()
    assert result  # True/False のみ確認
```

```python
# Good: 明確なアサーション
def test_good_assertion(self):
    result = some_function()
    assert result == "expected_value"
    assert len(result) > 0
    assert "key" in result
```

---

## まとめ

### テスト作成チェックリスト

- [ ] Exception Handler で例外処理を集約している
- [ ] Parametrized Testing で正常系・異常系を効率化している
- [ ] テストクラスで関連するテストをグループ化している
- [ ] Mock/Patch で外部依存を排除している
- [ ] Fixture で共通セットアップを再利用している
- [ ] テスト名とDocstringが明確である
- [ ] カバレッジ 80% 以上を達成している
- [ ] ruff チェックが通っている
- [ ] テストが独立している（実行順序に依存しない）

### 参考リンク

- [pytest documentation](https://docs.pytest.org/)
- [pytest parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
