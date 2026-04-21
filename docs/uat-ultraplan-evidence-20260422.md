# ULTRAPLAN UAT 実行エビデンス

**実行日時**: 2026-04-22  
**実行環境**: macOS M4 Pro, Python 3.12.11, uv  
**自動実行**: `uv run pytest tests/integration/test_ultraplan_flow.py -v`  

---

## 自動テスト結果 (12 件)

```
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up05_ultraplan_keyword_lowercase PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up05_ultraplan_keyword_uppercase PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up05_ultraplan_keyword_mixed_case PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up06_no_ultraplan_keyword PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up05_classifier_bypasses_llm PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP05KeywordRouting::test_up06_non_ultraplan_routes_to_general PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP04PlanFile::test_write_plan_creates_file PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP04PlanFile::test_exit_plan_mode_reads_plan_file PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP01CoordinatorDispatch::test_coordinator_dispatches_to_ultraplan_agent PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP01CoordinatorDispatch::test_coordinator_dispatches_ultraplan_case_insensitive PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP02UP03ApprovalFlow::test_up02_plan_approved_returns_plan_content PASSED
tests/integration/test_ultraplan_flow.py::TestUATUP02UP03ApprovalFlow::test_up03_plan_rejected_continues_loop PASSED

12 passed in 1.31s
```

総テスト数: **371 passed** (359 → 371, +12 件)

---

## 判定表

| テスト ID | タイトル | 自動/手動 | 判定 | 備考 |
|---|---|---|---|---|
| UAT-UP-01 | キーワードトリガー (Coordinator dispatch) | 自動 | ✅ PASS | `test_coordinator_dispatches_to_ultraplan_agent` |
| UAT-UP-02 | 承認フロー (`y`) | 自動 | ✅ PASS | `test_up02_plan_approved_returns_plan_content` |
| UAT-UP-03 | 却下・再計画フロー (`n`) | 自動 | ✅ PASS | `test_up03_plan_rejected_continues_loop` |
| UAT-UP-04 | `/tmp/ptsu-plan.md` 生成確認 | 自動 | ✅ PASS | `test_write_plan_creates_file` + `test_exit_plan_mode_reads_plan_file` |
| UAT-UP-05 | 大文字 `ULTRAPLAN` キーワード | 自動 | ✅ PASS | `test_up05_*` 3 件 |
| UAT-UP-06 | 非 ULTRAPLAN 通常ルーティング | 自動 | ✅ PASS | `test_up06_*` 2 件 |

---

## 手動テストが必要な項目

以下は TTY + 実 Anthropic API が必要なため自動化不可。手動で別途実施が必要。

| 項目 | 内容 | コマンド |
|---|---|---|
| 🖥️ 視覚確認 | `🧠 ULTRAPLAN — Deep investigation mode activated` の表示 | `uv run ptsu chat --coordinator --provider anthropic --no-stream` |
| 🖥️ 実プラン生成 | LLM が実際に `write_plan` → `exit_plan_mode` を呼ぶ | 上記コマンドで `ultraplan the src/ directory` と入力 |
| 🖥️ 承認ダイアログ | マゼンタパネルのプラン表示と `y/n` 入力 | 上記に続けて `y` を入力 |

---

## 注記

- `prompt_toolkit` (stdin prompt) と `rich.console.input()` が TTY を要求するため、
  `echo "..." \| uv run ptsu chat` 形式のパイプ実行は不可。
- 自動テストは実 API を使わず `MagicMock` で AnthropicProvider を差し替えて検証。
  承認・却下ロジックの分岐と状態遷移は完全に自動検証済み。
