---
date: 2026-04-24
phase: Day 11-14 完了後の振り返り
completed_steps:
  - scheduler/models.py (ScheduledTask)
  - scheduler/cron_utils.py (croniter ラッパ)
  - scheduler/storage.py (JSON永続化 + session store)
  - scheduler/idle.py (IdleTracker)
  - scheduler/runner.py (SchedulerDaemon)
  - agent/tools/schedule_tools.py (Create/List/Delete)
  - CLI/UI 統合 (app.py, ui.py)
  - 統合テスト (UAT-SCH-01〜11)
---

# Day 11-14 振り返り (Schedule Feature 実装)

## 実装内容

### 方針転換: KAIROS(watchdog 想定) → Schedule(cron)
`imple-plan.md` に書かれていた「KAIROS = ファイル監視 + ターミナルログ tail」は、
実は Claude Code の公開前推測だった。`claude-code-main/src/tools/ScheduleCronTool/` を調査した結果、
**本物の KAIROS は cron ベースのスケジューラ** であることが判明。
YAGNI 原則でまず cron だけ移植し、watchdog は将来機能に回した。

### Phase 1: ストレージ層
- `ScheduledTask` dataclass: id / cron / prompt / recurring / durable / created_at / last_fired_at / expires_at
- `ScheduleStore`: durable (JSON atomic write) + session-only (dict) の統合管理
- `MAX_JOBS=50` 上限
- `cron_utils.validate_cron` / `next_fire_time` / `compute_jitter_seconds` / `cron_to_human`
- `croniter` をラップして決定的ジッター (`:00`/`:30` 集中回避) を実装

### Phase 2: スケジューラデーモン
- `IdleTracker`: REPL の busy/idle を threading.Lock で管理
- `SchedulerDaemon`: `threading.Thread(daemon=True)` で 30 秒 tick
- `tick()` public 化してテスト可能性を確保
- `FireEvent` を `queue.Queue` に push、CLI 側が drain
- テスト用の `time_provider` コールバック注入

### Phase 3: ツール実装
- `ScheduleCreateTool` / `ScheduleListTool` / `ScheduleDeleteTool`
- `recurring=True` のデフォ 30 日自動失効
- 既存 `plan_tools.py` のパターンを踏襲

### Phase 4: CLI 統合
- `app.py`: 3 ツール登録 + デーモン起動 + `_drain_scheduler` ヘルパ
- `prompt.get_input()` の前後で `idle_tracker.set_idle(True/False)`
- 発火タスクはユーザー入力より優先して処理
- `finally` で `scheduler.stop()` を保証
- `ui.py`: `show_schedule_fired` / `show_schedule_created` を追加

### Phase 5: 統合テスト + ドキュメント
- `tests/integration/test_scheduler_flow.py`: UAT-SCH-01〜11 を自動化 (11 件)
- `docs/uat-schedule-specification.md`: 仕様書作成
- 新規テスト合計 +60 件 (unit 49 + integration 11)

## ✅ 良かった点

### 1. **Claude Code 本物の設計に忠実に従えた**
- `MAX_JOBS`, `DEFAULT_MAX_AGE_DAYS`, `:00/:30` ジッター回避など、実装上の細かい判断を参考にできた
- atomic write (tempfile + os.replace) も Claude Code の設計に準拠

### 2. **テスト駆動で境界条件を早期発見**
- `_base_time` の初回 `-1 minute` 誤実装を `test_tick_does_not_fire_before_due` が即検出
- croniter の `get_next` が「厳密に未来」を返す仕様を把握したうえで `created_at` をそのまま基準化できた

### 3. **時刻注入 (`time_provider`) による決定的テスト**
- `_FakeClock` で任意の時刻を再現可能
- threading.Thread をテストから分離することで、タイミング依存を排除

### 4. **プランの軌道修正に柔軟に対応**
- 当初 SENTINEL (watchdog) 方向だったが、調査結果を踏まえて Schedule (cron) に転換
- plan の「オープン項目」として名前や永続化ロケーションを残したまま実装に進めた

### 5. **既存テストをゼロ件壊さずに新機能追加**
- 389 → 449 (+60)、全既存 PASS を維持

## ❌ 悪かった点・改善点

### 1. **naive/aware datetime の扱いが冗長**
- `now.tzinfo is None` を毎回チェックして変換している箇所が複数
- `utc_iso_from_datetime` をヘルパ化したが、`_maybe_fire` / `_base_time` 内に重複した変換ロジックあり
- 将来: `datetime.utcnow()` を全面禁止し、内部を常に aware UTC に統一すべき

### 2. **cron_to_human が簡易実装**
- `0 9 * * 1-5` のような基本パターンしか対応していない
- 本家 Claude Code の `cronToHuman` はもっと複雑 (ステップ, 範囲, OR リスト等)
- coverage も 65% と低い (テスト不足)
- 改善: `cron-descriptor` パッケージを検討 (or テスト追加)

### 3. **CLI の `idle_tracker.set_idle(...)` の条件分岐が読みにくい**
- `idle_tracker.set_idle(True) if use_llm and runtime else None` は三項式でステートメント実行
- 本来は `if use_llm and runtime: idle_tracker.set_idle(True)` とすべき
- 改善: 次回コミットでリファクタ

### 4. **`scheduler` 変数のスコープ依存が脆弱**
- `finally` で `if "scheduler" in locals():` チェックしている
- use_llm=False のパスではデーモン起動しないため `scheduler` が未定義
- 改善: `scheduler: SchedulerDaemon | None = None` で関数冒頭で初期化

### 5. **手動 UAT (UAT-SCH-M01) 未実施**
- 実 API で「1分後に発火」を確認していない
- CLI の `idle_tracker` 連携が実動作するか未検証
- 次回: コミット後に手動実施

### 6. **ScheduleStore._load_durable が例外時に空状態を返す**
- JSON 破損時は `ScheduleStoreError` を送出するが、CLI 側でキャッチしていない
- ユーザーが不正に編集したファイルで CLI が起動不能になる可能性
- 改善: CLI 側で破損 JSON をバックアップしてから空で起動する fallback を追加

## 📊 メトリクス
- テスト数: 449 件 (+60 件)
- カバレッジ: scheduler/models 100%, storage 99%, idle 100%, runner 93%, cron_utils 86%
- 新規ファイル: 8 (`scheduler/` 5 + `schedule_tools.py` + テスト 2)
- 変更ファイル: 3 (`pyproject.toml`, `cli/app.py`, `cli/ui.py`)
- 依存追加: `croniter>=2.0.0` (+ `python-dateutil`, `six` 推移依存)

## 🎓 学んだこと

1. **imple-plan は推測込みなので鵜呑みにしない**: Claude Code の公開ソースを見ないと「本物の仕様」は分からない。名前だけ合っても中身が違うことはよくある。
2. **croniter の `get_next` は厳密に未来**: `base == target` でも次の発火時刻を返す。基準時刻をそのまま使えば重複発火を回避できる。
3. **`threading.Thread(daemon=True)` + `Event.wait(timeout)` の組み合わせ**: polling ループで sleep より優雅。stop シグナルで即抜けできる。
4. **public `tick()` メソッド**: バックグラウンドスレッド本体を直接テストせず、`tick` だけを単体テスト対象にするとタイミング依存がゼロになる。
5. **atomic file write**: `tempfile.NamedTemporaryFile(delete=False) + os.replace` で中途半端な書き込みを防げる。同一 FS 上の tempfile が必須。

## 🔜 次のステップへの示唆

### 短期 (次コミットで対応)
- [ ] CLI の `idle_tracker` セット条件をリファクタ (三項式 → if 文)
- [ ] `scheduler` 変数をループ外で明示的に初期化
- [ ] 手動 UAT-SCH-M01 実施 + エビデンス記録

### 中期 (Day 15+ 候補)
- [ ] Scheduled タスク発火時に Coordinator モードに自動投入 (現在は raw prompt)
- [ ] `cron_to_human` の改善または `cron-descriptor` 導入
- [ ] `JSON 破損 → backup + 空起動` の fallback
- [ ] watchdog (ファイル監視) 機能を別モジュール `watcher/` として追加 (imple-plan の B 案)

### 長期 (Week 3 BUDDY / Dream System に影響)
- スケジュールされた「Dream タスク」(深夜に対話履歴要約) を Schedule 機能で実現できる
- BUDDY のイベント (毎朝挨拶など) も Schedule で実装可能
