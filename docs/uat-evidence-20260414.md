# PTSU UAT 実行エビデンス

**実行日時**: 2026-04-14  
**対象バージョン**: 0.1.0  
**実行環境**: macOS (M4 Pro), Python 3.12, uv  
**対象範囲**: UAT-01〜09（CLI基盤 + LLMモード前半）

---

## UAT-01: バージョン表示

**コマンド**:
```bash
uv run ptsu version
```

**実行結果**:
```
PTSU version 0.1.0
```

**終了コード**: 0  
**判定**: ✅ PASS

---

## UAT-02: ヘルプ表示

**コマンド**:
```bash
uv run ptsu --help
uv run ptsu chat --help
```

**実行結果** (`ptsu --help`):
```
Usage: ptsu [OPTIONS] COMMAND [ARGS]...

 PTSU - AI Agent CLI tool

╭─ Options ──────────────────────╮
│ --help  Show this message and exit. │
╰────────────────────────────────╯
╭─ Commands ─────────────────────╮
│ chat     対話モードを起動する。 │
│ version  バージョン情報を表示する。 │
╰────────────────────────────────╯
```

**実行結果** (`ptsu chat --help`):
```
Usage: ptsu chat [OPTIONS]

 対話モードを起動する。

╭─ Options ──────────────────────────────────────────────────────────╮
│ --verbose      -v                Enable verbose output             │
│ --llm              --no-llm      Enable LLM mode [default: llm]   │
│ --provider                 TEXT  LLM provider (openai or anthropic)│
│ --stream           --no-stream   Enable streaming [default: stream]│
│ --coordinator  --no-coordinator  Enable Coordinator Mode           │
│ --help                           Show this message and exit.       │
╰────────────────────────────────────────────────────────────────────╯
```

**終了コード**: 0  
**確認項目**:
- [x] `chat` サブコマンド表示
- [x] `version` サブコマンド表示
- [x] `--llm/--no-llm` オプション
- [x] `--stream/--no-stream` オプション
- [x] `--coordinator/--no-coordinator` オプション
- [x] `--provider` オプション
- [x] `--verbose/-v` オプション

**判定**: ✅ PASS

---

## UAT-03: ウェルカム画面

**コマンド**:
```bash
printf "exit\n" | uv run ptsu chat --no-llm
```

**実行結果**:
```
╭──────────────────────────────────────────────────╮
│                                                  │
│  PTSU - AI Agent CLI                             │
│                                                  │
│  Version: 0.1.0                                  │
│  Type 'exit' or 'quit' to exit, Ctrl+D to quit  │
│  Type 'help' for available commands              │
│                                                  │
╰──────────────────────────────────────────────────╯

ℹ Chat mode started. Type your message and press Enter.
You > exit
ℹ Goodbye!
```

**終了コード**: 0  
**確認項目**:
- [x] パネル（枠付き）装飾表示
- [x] `PTSU - AI Agent CLI` タイトル
- [x] バージョン番号 `0.1.0`
- [x] 終了方法の案内（exit/quit/Ctrl+D）
- [x] `help` コマンドの案内

**判定**: ✅ PASS

---

## UAT-04: エコーモード

**コマンド**:
```bash
printf "Hello PTSU\nテストメッセージ\nexit\n" | uv run ptsu chat --no-llm
```

**実行結果**:
```
...（ウェルカム画面）...
ℹ Chat mode started. Type your message and press Enter.
You > Hello PTSU
Assistant: Echo: Hello PTSU
You > テストメッセージ
Assistant: Echo: テストメッセージ
You > exit
ℹ Goodbye!
```

**終了コード**: 0  
**確認項目**:
- [x] 入力が `Echo: <入力>` 形式でエコーバックされる
- [x] 日本語メッセージが正しくエコーバックされる

**判定**: ✅ PASS

---

## UAT-05: exit / quit / Ctrl+D による終了

### exit コマンド

**コマンド**:
```bash
printf "exit\n" | uv run ptsu chat --no-llm
```

**実行結果**:
```
You > exit
ℹ Goodbye!
```

**終了コード**: 0 — ✅ PASS

### quit コマンド

**コマンド**:
```bash
printf "quit\n" | uv run ptsu chat --no-llm
```

**実行結果**:
```
You > quit
ℹ Goodbye!
```

**終了コード**: 0 — ✅ PASS

### Ctrl+D (EOF)

**コマンド**:
```bash
printf "" | uv run ptsu chat --no-llm
```

**実行結果**:
```
You >
ℹ Goodbye!
```

**終了コード**: 0 — ✅ PASS

**判定**: ✅ PASS（3通りすべて正常終了）

---

## UAT-06: help コマンド

**コマンド**:
```bash
printf "help\nexit\n" | uv run ptsu chat --no-llm
```

**実行結果**:
```
System: Available commands:
  - exit, quit: Exit the chat
  - help: Show this help message
  - Echo mode: Messages are echoed back
```

**終了コード**: 0  
**確認項目**:
- [x] exit/quit の説明
- [x] help の説明
- [x] Echo mode の説明

**判定**: ✅ PASS

---

## UAT-07: LLMモード起動

**コマンド**:
```bash
printf "exit\n" | uv run ptsu chat
```

**実行結果**:
```
ℹ LLM mode enabled (openai) with 6 tools available.
ℹ Chat mode started. Type your message and press Enter.
You > exit
ℹ Goodbye!
```

**終了コード**: 0  
**確認項目**:
- [x] `LLM mode enabled (openai)` 表示
- [x] `6 tools available` — 登録ツール数が正確（read_file, write_file, execute_command, grep_search, find_files, list_directory）

**判定**: ✅ PASS

---

## UAT-08: 基本的な質問応答

**コマンド**:
```bash
printf "Pythonで1+1を計算するコードを1行で書いて\nexit\n" | uv run ptsu chat --no-stream
```

**実行結果**:
```
Assistant: Pythonで1+1を計算するコードは以下のように書けます。

```python
result = 1 + 1
```

**終了コード**: 0  
**確認項目**:
- [x] `Assistant:` プレフィックス付きで応答が返る
- [x] 応答にPythonコードが含まれる
- [x] LLMエラーなし

**判定**: ✅ PASS

---

## UAT-09: APIキーなし時のフォールバック

**コマンド**:
```bash
printf "Hello\nexit\n" | PTSU_OPENAI_API_KEY="" uv run ptsu chat
```

**実行結果**:
```
Error: OpenAI API key is not configured. Set PTSU_OPENAI_API_KEY environment variable.
ℹ Falling back to echo mode. Use --no-llm to suppress this message.
...
Assistant: Echo: Hello
```

**終了コード**: 0  
**確認項目**:
- [x] APIキー未設定エラーメッセージが表示される
- [x] `Falling back to echo mode.` メッセージが表示される
- [x] エコーモードで継続動作する（クラッシュしない）

**判定**: ✅ PASS

---

## サマリー

| ID | テスト名 | 結果 | 備考 |
|---|---|---|---|
| UAT-01 | バージョン表示 | ✅ PASS | `PTSU version 0.1.0` |
| UAT-02 | ヘルプ表示 | ✅ PASS | 全5オプション確認済み |
| UAT-03 | ウェルカム画面 | ✅ PASS | パネル装飾・バージョン・案内文 |
| UAT-04 | エコーモード | ✅ PASS | 日本語含む |
| UAT-05 | exit/quit/Ctrl+D | ✅ PASS | 3通りすべて正常終了 |
| UAT-06 | help コマンド | ✅ PASS | 全コマンド一覧表示 |
| UAT-07 | LLMモード起動 | ✅ PASS | 6ツール登録確認 |
| UAT-08 | 基本質問応答 | ✅ PASS | Pythonコード生成 |
| UAT-09 | APIキーなしフォールバック | ✅ PASS | エコーモードへ継続 |

**結果: 9/9 PASS** ✅

---

## 未実施テスト（後半: UAT-10〜22）

| ID | テスト名 | 状態 | 備考 |
|---|---|---|---|
| UAT-10 | ファイル読み取り | ⏳ 未実施 | 承認不要・自動化可 |
| UAT-11 | ファイル書き込み（承認あり）| ⏳ 未実施 | **手動承認が必要** |
| UAT-12 | コマンド実行（承認あり）| ⏳ 未実施 | **手動承認が必要** |
| UAT-13 | grep 検索 | ⏳ 未実施 | 自動化可 |
| UAT-14 | ファイル検索 | ⏳ 未実施 | 自動化可 |
| UAT-15 | ディレクトリ一覧 | ⏳ 未実施 | 自動化可 |
| UAT-16 | ストリーミング応答 | ⏳ 未実施 | 自動化可 |
| UAT-17 | ストリーミング無効化 | ⏳ 未実施 | 自動化可 |
| UAT-18 | Coordinator Mode 起動 | ⏳ 未実施 | 自動化可 |
| UAT-19 | SEARCH インテント | ⏳ 未実施 | API依存 |
| UAT-20 | CODE インテント | ⏳ 未実施 | **手動承認が必要** |
| UAT-21 | EXECUTE インテント | ⏳ 未実施 | **手動承認が必要** |
| UAT-22 | MULTI インテント | ⏳ 未実施 | **手動承認が必要** |
