---
date: 2026-04-07
phase: Day 3 完了後の振り返り
---

# Day 3 振り返り（承認フロー + 進捗表示）

## 実装内容

### Step 2: Human-in-the-Loop 承認フロー
- `ApprovalManager`: ツール実行の承認管理
- `Tool.requires_approval`: 破壊的操作の判定プロパティ
- 承認UI: Rich Panel で見やすい表示
- 3択対応: [Y]es / [N]o / [A]lways

### Step 3: ツール進捗表示
- `show_tool_execution()`: ツール実行開始時の表示
- `show_tool_result()`: ツール実行結果の表示
- リアルタイムフィードバック

## ✅ 良かった点

### 1. **設計の疎結合性**
- コールバック関数で CLI と Runtime を分離
- `request_approval_callback` と `show_progress_callback` の導入
- テスタビリティが高い（ApprovalManager は 100% カバレッジ）

**理由**: 
- CLI層とAgent層が独立しているため、将来的なUI変更が容易
- テストが書きやすく、バグが少ない

### 2. **段階的な実装**
- Step 2 → Step 3 の順で実装
- 各ステップでテストを実行し、動作確認
- コミットを分けることで、問題発生時のロールバックが容易

**理由**:
- 一度に多くを実装すると、バグの原因特定が困難
- 小さな成功体験を積み重ねることで、モチベーション維持

### 3. **Rich UI の活用**
- Panel, Table を使った見やすい承認リクエスト
- 色分けで視認性向上（yellow=ツール名, dim=引数）
- 長い値は自動省略（100文字制限）

**理由**:
- ユーザー体験が大幅に向上
- プロフェッショナルな見た目

### 4. **テストカバレッジの向上**
- Phase 1: 30% → Day 3: 62%
- ApprovalManager: 100% カバレッジ
- 全87テスト PASSED

**理由**:
- バグの早期発見
- リファクタリングの安全性確保

## ❌ 悪かった点・改善点

### 1. **承認フローのUXが未完成**
**問題**:
- 承認リクエストが毎回表示される（同じツールでも）
- "Always approve" が効いているか分かりにくい
- 承認済みツールのリストが見えない

**改善案**:
```python
# 承認済みツールを表示する機能
def show_approved_tools(manager: ApprovalManager):
    if manager._auto_approved_tools:
        console.print("[dim]Auto-approved tools:[/dim]", ", ".join(manager._auto_approved_tools))
```

**Day 4以降での対応**:
- セッション開始時に承認済みツールを表示
- `help` コマンドで承認状態を確認可能に

### 2. **進捗表示の情報量が不足**
**問題**:
- ツール実行時間が分からない
- 複数ツールが並行実行される場合の表示が未対応
- エラー時の詳細情報が不足

**改善案**:
```python
# 実行時間を表示
import time
start = time.time()
# ... ツール実行 ...
elapsed = time.time() - start
console.print(f"[dim]✓[/dim] [green]{tool_name}[/green] ({elapsed:.2f}s)")
```

**Day 4以降での対応**:
- ストリーミング実装時に、実行時間を追加
- エラー時のスタックトレース表示オプション

### 3. **テストの環境依存性**
**問題**:
- `.env` ファイルの影響でテストが失敗
- `test_config.py` で `monkeypatch.chdir(tmp_path)` が必要だった

**改善案**:
```python
# pytest.ini または pyproject.toml で環境変数をクリア
[tool.pytest.ini_options]
env = [
    "PTSU_OPENAI_API_KEY=",
    "PTSU_ANTHROPIC_API_KEY=",
]
```

**Day 4以降での対応**:
- テスト用の設定ファイルを分離
- `pytest-env` プラグインの導入を検討

### 4. **ドキュメント不足**
**問題**:
- 承認フローの使い方が README に記載されていない
- 新規ツールの追加方法が不明確
- アーキテクチャ図がない

**改善案**:
- `docs/architecture.md` を作成
- `docs/adding-tools.md` でツール追加手順を記載
- README に承認フローのスクリーンショットを追加

**Day 4以降での対応**:
- Day 4 完了後にドキュメント整備
- E2E テスト実施時にスクリーンショット取得

### 5. **エラーハンドリングの一貫性**
**問題**:
- 承認拒否時のメッセージが簡素すぎる
- ツール実行失敗時の再試行機能がない
- エラーログが不十分

**改善案**:
```python
# 承認拒否時に理由を記録
if decision == "n":
    logger.info(f"Tool {function_name} rejected by user")
    results.append(
        Message(
            role="tool",
            content=f"Tool execution rejected by user. The assistant should try an alternative approach.",
            tool_call_id=tool_call["id"],
            name=function_name,
        )
    )
```

**Day 4以降での対応**:
- ロギング機能の強化
- エラー時の代替手段の提案

## 📊 メトリクス

| 項目 | Phase 1 | Day 3 | 改善 |
|------|---------|-------|------|
| テスト数 | 33 | 87 | +164% |
| カバレッジ | 30% | 62% | +32pt |
| ツール数 | 3 | 3 | - |
| 実装時間 | - | ~2h | - |

## 🎯 Day 4 への教訓

### DO（続けるべきこと）
1. ✅ **段階的実装**: 小さなステップで確実に進める
2. ✅ **テストファースト**: 実装前にテストケースを考える
3. ✅ **疎結合設計**: コールバックで層を分離
4. ✅ **Rich UI活用**: 見た目の良さは重要

### DON'T（避けるべきこと）
1. ❌ **環境依存テスト**: `.env` ファイルの影響を受けないように
2. ❌ **ドキュメント後回し**: 実装と同時に更新
3. ❌ **UX の妥協**: 細かい使い勝手も重要
4. ❌ **エラーメッセージの手抜き**: ユーザーに分かりやすく

### TRY（新しく試すこと）
1. 🆕 **ストリーミング**: リアルタイム応答で体感速度向上
2. 🆕 **プロンプト設計**: エージェントの振る舞いを安定化
3. 🆕 **実行時間計測**: パフォーマンス可視化
4. 🆕 **ロギング強化**: デバッグ効率向上

## 次のステップ

Day 4 では以下を実装:
1. **Step 4: 検索ツール** ✅ 完了
2. **Step 1: ストリーミング応答** ← 次
3. **Step 5: プロンプト設計** ← 次

Day 3 の教訓を活かし、より実用的なエージェントを目指す。
