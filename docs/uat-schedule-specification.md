---
tags:
  - uat
  - schedule
  - day11-14
phase: Day 11-14
target: Schedule feature (cron-based agent triggers)
---

# UAT Specification: Schedule Feature (Cron-based Agent Triggers)

## 概要

Claude Codeの KAIROS (ScheduleCronTool) 相当の機能を ptsu-code に実装。
ユーザーが自然言語で依頼した内容を、LLMが cron 式でスケジュール実行できるかを検証する。

## 対象機能

- `schedule_create` — プロンプトを cron 式でスケジュール
- `schedule_list` — 登録済みタスクの一覧
- `schedule_delete` — タスクの削除
- バックグラウンドデーモン — REPL idle 時のみ発火
- 永続化 — `.ptsu/scheduled_tasks.json` (durable タスクのみ)

## テストシナリオ

### UAT-SCH-01: durable タスクの作成と永続化
**目的**: `durable=true` でタスクが JSON ファイルに保存されること

**手順**:
1. `schedule_create(cron="0 9 * * *", prompt="daily", durable=true)` を実行
2. `.ptsu/scheduled_tasks.json` の存在を確認
3. ファイル内容に作成したタスクが含まれることを確認

**期待結果**: JSON ファイルが作成され、`tasks[0].prompt == "daily"`

**自動化**: `tests/integration/test_scheduler_flow.py::test_uat_sch_01_create_persists_json`

---

### UAT-SCH-02: タスク一覧
**目的**: `schedule_list` で登録済みタスクが表示されること

**手順**:
1. 2つのタスクを作成
2. `schedule_list` を呼び出す

**期待結果**: 両方のタスクが出力に含まれる

**自動化**: `test_uat_sch_02_list_shows_entries`

---

### UAT-SCH-03: タスク削除
**目的**: `schedule_delete` で指定IDのタスクが削除されること

**手順**:
1. タスクを作成し ID を取得
2. `schedule_delete(id=<task_id>)` を実行
3. ストアからタスクが消えることを確認

**期待結果**: `store.count() == 0`

**自動化**: `test_uat_sch_03_delete_removes_task`

---

### UAT-SCH-04: recurring vs one-shot の動作
**目的**: `recurring=True` は発火後も残り、`False` は削除されること

**手順**:
1. `recurring=True` タスクと `recurring=False` タスクを作成
2. `tick()` を呼んで発火させる
3. ストアを確認

**期待結果**:
- recurring タスクは残存、`last_fired_at` が更新される
- one-shot タスクは削除される
- 再 tick で recurring のみ再発火

**自動化**: `test_uat_sch_04_recurring_refires_one_shot_auto_removes`

---

### UAT-SCH-05: セッション横断の永続化
**目的**: `durable=True` タスクが新セッションで復元されること

**手順**:
1. セッション1で `durable=True` タスクを作成
2. セッション2(新 ScheduleStore インスタンス) で同じファイルをロード
3. タスクが存在することを確認

**期待結果**: セッション2で `count() == 1`

**自動化**: `test_uat_sch_05_durable_survives_session`

---

### UAT-SCH-06: session-only タスクは引き継がれない
**目的**: `durable=False` タスクは新セッションで消えること

**自動化**: `test_uat_sch_06_session_only_does_not_survive`

---

### UAT-SCH-07: MAX_JOBS 制限
**目的**: 50タスクを超える登録が拒否されること

**自動化**: `test_uat_sch_07_max_jobs_enforced`

---

### UAT-SCH-08: REPL busy 時は発火しない
**目的**: `is_idle=False` のとき tick で発火しないこと

**自動化**: `test_uat_sch_08_busy_repl_blocks_fire`

---

### UAT-SCH-09: 有効期限切れタスクの削除
**目的**: `expires_at` を過ぎたタスクが発火せず削除されること

**自動化**: `test_uat_sch_09_expired_recurring_removed`

---

### UAT-SCH-10: 不正な cron 式の拒否
**目的**: `validate_cron` で無効な式が弾かれること

**自動化**: `test_uat_sch_10_invalid_cron_rejected`

---

### UAT-SCH-11: recurring の auto-expire
**目的**: `recurring=True` で 30 日の expires_at が設定されること

**自動化**: `test_uat_sch_11_expires_at_set_for_recurring`

---

## 手動テスト (実API + TTY)

### UAT-SCH-M01: 自然言語からのスケジュール作成 (手動)
**目的**: LLM が自然言語依頼から適切な cron 式を生成し、ツールを呼び出せるか

**手順**:
```bash
uv run ptsu chat --coordinator --provider anthropic --no-stream
You > 1分後に「こんにちは」と出力する one-shot タスクをスケジュールして
```

**期待結果**:
- LLM が `schedule_create` を `recurring=false` + 適切な cron で呼び出す
- タスク作成の成功メッセージが表示される
- 約1分後に「⏰ Scheduled Task Fired」パネルが表示され、"こんにちは" を含む応答が出力される

**注意**: REPL が idle(入力待ち) になっていないと発火しないため、タスク作成後は入力せず待つこと。

---

## 最終判定表 (テンプレート)

| テスト ID | タイトル | 自動/手動 | 判定 | 備考 |
|---|---|---|---|---|
| UAT-SCH-01 | durable 永続化 | 自動 | ✅/❌ | |
| UAT-SCH-02 | list 表示 | 自動 | ✅/❌ | |
| UAT-SCH-03 | delete 動作 | 自動 | ✅/❌ | |
| UAT-SCH-04 | recurring/one-shot | 自動 | ✅/❌ | |
| UAT-SCH-05 | durable 引き継ぎ | 自動 | ✅/❌ | |
| UAT-SCH-06 | session-only 非永続 | 自動 | ✅/❌ | |
| UAT-SCH-07 | MAX_JOBS 制限 | 自動 | ✅/❌ | |
| UAT-SCH-08 | busy 時非発火 | 自動 | ✅/❌ | |
| UAT-SCH-09 | 期限切れ削除 | 自動 | ✅/❌ | |
| UAT-SCH-10 | 不正 cron 拒否 | 自動 | ✅/❌ | |
| UAT-SCH-11 | auto-expire 30日 | 自動 | ✅/❌ | |
| UAT-SCH-M01 | 実API 1分後発火 | 手動 | ⏳ | 未実施 |
