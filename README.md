# PTSU

AI エージェント CLI ツール

## 機能

- **Coordinator Mode**: マルチエージェント・ルーター
- **ULTRAPLAN**: 長時間思考モード
- **KAIROS**: 常時監視・自律実行
- **Dream System**: 記憶の整理と最適化
- **BUDDY**: AI ペット＆ガチャ要素

## インストール（マシン全体で使う）

```bash
# 初回インストール — どのディレクトリからでも ptsu コマンドが使えるようになる
uv tool install /path/to/ptsu-code

# eval ダッシュボード (streamlit) も含める場合
uv tool install --extra eval /path/to/ptsu-code

# バージョン確認
ptsu version
```

`~/.local/bin` が `PATH` に含まれていない場合は `.zshrc` に追加:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## アップデート

```bash
# コードを変更・コミット後
git tag v0.X.Y
uv tool install --reinstall /path/to/ptsu-code
ptsu version  # 新バージョンを確認
```

## バージョンポリシー (SemVer: MAJOR.MINOR.PATCH)

| 桁 | 上げるタイミング | 例 |
|---|---|---|
| **MAJOR** | 破壊的変更（CLI / 設定 / `~/.ptsu/` データ形式の非互換） | コマンド体系の刷新、設定スキーマ変更 |
| **MINOR** | 新機能追加（後方互換あり） | 新プロバイダー対応、新ツール追加 |
| **PATCH** | バグ修正・テスト・リファクタ | ツール呼び出しの修正、カバレッジ補完 |

> `0.x` 系は開発版: MINOR 上げで破壊的変更を許容（SemVer 標準）。`1.0.0` は CLI・設定・データ形式が安定した時点で切る。

## セットアップ（開発）

### ローカル環境

```bash
# 依存関係のインストール
uv sync --all-extras

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定

# CLIの起動（OpenAI）
export PTSU_OPENAI_API_KEY=your-api-key
uv run ptsu chat

# CLIの起動（Anthropic）
export PTSU_ANTHROPIC_API_KEY=your-api-key
uv run ptsu chat --provider anthropic

# エコーモード（APIキー不要）
uv run ptsu chat --no-llm

# バージョン確認
uv run ptsu version
```

### 対応プロバイダー

- **OpenAI** (デフォルト): GPT-4o-mini
- **Anthropic**: Claude 3.5 Sonnet

### Docker環境

```bash
# イメージのビルド
docker compose build

# 対話モードの起動
docker compose run --rm dev

# テストの実行
docker compose run --rm dev pytest
```

## 開発

### テストの実行

```bash
uv run pytest
```

### コード品質チェック

```bash
# Lintチェック
uv run ruff check src/ tests/

# 自動修正
uv run ruff check --fix src/ tests/
```

## プロジェクト構成

```
ptsu-code/
├── src/
│   └── ptsu_code/
│       ├── cli/          # CLIフロントエンド
│       ├── agent/        # エージェント層 (Day 3~)
│       └── tools/        # ツール層 (Day 3~)
├── tests/
├── docs/
└── docker-compose.yml
```

## ライセンス

MIT
