---
date: 2026-05-02
phase: Day 18-25 完了後の振り返り
completed_steps:
  - Dream System 設計ドキュメント (day18-21-memory-design.md)
  - Phase 1: SessionMemoryConfig / SessionMemoryState / Template / Storage
  - Phase 2: Triggers (should_extract)
  - Phase 3: MemoryExtractor (LLM 呼び出し + fallback)
  - Phase 4: SessionMemoryManager (オーケストレーター)
  - Phase 5: cli/app.py 統合 (注入・ターン追加・終了時アーカイブ)
  - Phase 6: /summary ツール (MemorySummaryTool)
  - OllamaProvider + ハイブリッドメモリ抽出 (--local-memory)
  - ProviderProber — 起動時可用性チェック + graceful fallback
---

# Day 18-25 振り返り（Dream System + Local AI Integration）

## 実装内容

### Step 1: Dream System 設計 (Day 18)
- Claude Code の SessionMemory を調査し、ptsu-code 向けの設計ドキュメントを作成
- 固定 10 セクションテンプレート、トークン閾値 (8k init / 4k update)、アトミック書き込みの方針確定

### Step 2: SessionMemory コアモジュール (Day 18-20)
- `models.py`: `SessionMemoryConfig` / `SessionMemoryState` で設定・状態を分離
- `template.py`: Claude Code 準拠の 10 セクション Markdown テンプレート
- `storage.py`: `~/.ptsu/session-memory/current.md` へのアトミック書き込み + archive
- `triggers.py`: `estimate_tokens()` + `should_extract()` — トークン数とツール呼び出し数の複合閾値
- `extractor.py`: LLM 呼び出しによる抽出、空レスポンス時 fallback
- `manager.py`: 全モジュールのオーケストレーター

### Step 3: CLI 統合 (Day 20-21)
- `app.py`: 起動時に前回メモリを system prompt に注入、各ターン後に `add_turn + maybe_extract`、終了時 `finalize`
- `/summary` スラッシュコマンド追加
- `MemorySummaryTool`: LLM が自律的に呼び出せるツールとして登録

### Step 4: OllamaProvider (Day 22-25)
- `OpenAIProvider` に `base_url` パラメータ追加 (OpenAI 互換エンドポイント汎用化)
- `OllamaProvider`: `OpenAIProvider` を継承、`api_key="ollama"`, デフォルト `localhost:11434/v1`
- `Settings`: `PTSU_OLLAMA_BASE_URL / MODEL_FAST / MODEL_SMART` 環境変数追加
- `AgentRuntime`: `--provider ollama` ルート追加 (API キーチェックをスキップ)
- `--local-memory` フラグ: 会話は cloud LLM、メモリ抽出だけ Ollama にオフロードするハイブリッド構成

### Step 5: ProviderProber (Day 25)
- `probe.py`: `ProviderAvailability` / `AvailableProviders` / `probe_providers()` — 全プロバイダー可用性を一括チェック
  * openai / anthropic: API キー有無
  * ollama: HTTP GET `localhost:11434/` (2秒 timeout)
- `cli/ui.py`: `show_provider_availability()` — ✓/✗ カラー表示
- `cli/app.py`: 起動時プローブ → 指定プロバイダー不可なら echo fallback
- `--local-memory` + Ollama 未起動 → 自動的に main provider にフォールバック + 警告表示

---

## ✅ 良かった点

### 1. **TDD の徹底**
- 各フェーズで先にテストを設計し、56 → 62 → 531 と積み上げた
- モックが明確な境界 (LLMProvider) に集中しており、テストが壊れにくい

### 2. **Claude Code に忠実な設計**
- 固定テンプレート・トークン閾値・アトミック書き込みは調査ドキュメントのエッセンスを正確に反映
- セクション保全チェック (`is_valid_memory`) で LLM が構造を壊せない設計

### 3. **OllamaProvider の薄さ**
- `OpenAIProvider` の `base_url` 引数だけで互換実装が完成し、コード重複ゼロ
- 将来 vLLM や LocalAI にも同じ方法で対応できる

### 4. **ハイブリッド設計の実用性**
- `--local-memory` フラグで「メイン会話 = cloud、メモリ抽出 = Ollama」という明確な責務分離
- 環境変数でモデルと URL を上書き可能なため、様々な Ollama セットアップに対応

---

## ❌ 悪かった点・改善点

### 1. **Ollama の起動が前提条件のまま → ✅ 解決済み**
- **問題**: `--provider ollama` / `--local-memory` 時に Ollama が未起動だと `httpx.ConnectError` が発生し、ptsu のエラーメッセージとして出てこない
- **対応**: `ProviderProber` を実装。起動時に HTTP ping で Ollama 可用性をチェックし、不可なら明確なエラー表示 / graceful fallback を実施
- **残課題**: Ollama がセッション途中で落ちた場合のリトライハンドリングは未実装

### 2. **manager.py L154 が未カバー**
- `force_extract` で「変化なし & 空でない」パスがテスト困難
- 実害は少ないが、テスト追加で 100% にできる

### 3. **テスト名が長すぎる箇所**
- `test_extract_returns_provider_response` など、クラス単位でまとめているが命名の一貫性が不均一
- 次のモジュールから `describe_xxx / it_xxx` パターンに統一するかを検討

### 4. **stream + memory の組み合わせが未テスト**
- `app.py` のストリーミングパスで `add_turn / maybe_extract` が動く保証がテストレベルにない
- CLI 統合テストを追加する必要がある

### 5. **Ollama セッション中の断絶に未対応**
- 起動時チェックは完了したが、セッション途中で Ollama が落ちるケースのリトライは未実装
- `maybe_extract()` が失敗した場合のロギングと自動フォールバックが必要

---

## 📊 メトリクス

| 指標 | 値 |
|------|-----|
| テスト数 | 547件 (+88件) |
| カバレッジ | 88% (→ 88% 維持) |
| 新規ファイル数 | 16 |
| コミット数 | 6 |
| memory パッケージカバレッジ | 98-100% |
| probe.py カバレッジ | 16 テスト |

---

## 🎓 学んだこと

1. **Ollama は OpenAI SDK の `base_url` 1 行で済む** — 互換レイヤーを自前実装する必要はない
2. **ハイブリッド設計はプロバイダー注入パターンで簡潔に表現できる** — 単一責任の `SessionMemoryManager(provider=...)` に差し込むだけ
3. **アトミック書き込み (`tmp → rename`) はセッション中断時のファイル破損を防ぐ鍵** — 実装コストが低い割に信頼性への貢献が大きい
4. **テストの `strip()` と実装の `.strip()` の一致確認は見落としやすい** — 文字列の末尾処理は常に明示的に
5. **プロバイダー探索は起動時に一度だけ実行するのが正解** — セッション中は結果をキャッシュして参照するだけで十分
6. **ユーザーの「運営方法」という視点が重要** — コードの正しさだけでなく、ユーザーが実際に使うシーン（Ollama 未起動、キー未設定等）を先に考えてから実装する

---

## 🔜 次のステップへの示唆

- **Day 26-28**: プロンプトエンジニアリング — Ollama でも Tool Calling が安定するための JSON スキーマ制約調整
- **Day 29-30**: Evaluation UX (Streamlit ダッシュボード) — タスク成功率・コスト可視化
- **セッション中断絶ハンドリング**: `maybe_extract()` 失敗時のリトライ + ロギング
- **運用**: macOS launchd で `ollama serve` をデーモン化 (`brew services start ollama`) 推奨
