# PTSU - Claude Code Clone

Claude Code の未公開機能を完全再現した AI エージェント CLI

## 機能

- **Coordinator Mode**: マルチエージェント・ルーター
- **ULTRAPLAN**: 長時間思考モード
- **KAIROS**: 常時監視・自律実行
- **Dream System**: 記憶の整理と最適化
- **BUDDY**: AI ペット＆ガチャ要素

## セットアップ

### ローカル環境

```bash
# 依存関係のインストール
uv sync --all-extras

# CLIの起動
uv run ptsu chat

# バージョン確認
uv run ptsu version
```

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
