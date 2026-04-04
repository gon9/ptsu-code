---
tags:
  - project_plan
  - claude_code
  - ai_agent
aliases:
  - Claude Code Clone 開発計画
---

# 30-Day Project Plan: Claude Code Clone with Unreleased Features

Claude Codeの未公開機能（マルチエージェント、長時間思考、常時監視、記憶整理、エンタメ要素）を完全再現し、最終的にMac M4 Proのローカル環境で自律稼働する最強のCLI相棒（AIエージェント）を開発する30日間のプロジェクト計画です。

## 1. プロジェクト概要 (Objective)
ターミナル上で動作するAIエージェントCLIをゼロから構築します。Claude Codeのソースコードから判明した強力なコンセプトを独自解釈で実装し、「単なるコマンド実行ボット」から「自律的に思考し、共に成長する開発パートナー」へと昇華させます。

## 2. 機能定義 (Feature Scope)
以下の5つのコア機能を中心に開発を進めます。

1. **Coordinator Mode (マルチエージェント・ルーター)**
   - ユーザーの曖昧な指示を解釈し、「調査(Search)」「コーディング(Coder)」「実行(Executor)」などのSub-agentにタスクを分割・委譲する司令塔機能。
2. **ULTRAPLAN (長時間思考モード)**
   - 複雑なアーキテクチャ設計や大規模リファクタリングの際、即座に回答せず、最長30分間バックグラウンドで思考（ツールの反復実行、検証、仮説立て）を続けるモード。
3. **KAIROS (常時監視・自律実行)**
   - ターミナルのエラー出力や、指定ディレクトリのファイル変更（TODOコメントの追加など）をバックグラウンドで監視し、ユーザーが指示する前に自律的に解決案を提示するデーモン機能。
4. **Dream System (記憶の整理と最適化)**
   - エージェントがアイドル状態のとき（夜間など）に、その日の対話履歴や失敗したコマンド実行結果を要約・構造化し、長期記憶（RAGやJSONファイル）として保存・最適化する機能。
5. **BUDDY (AIペット＆ガチャ要素)**
   - CLI上にアスキーアートやRichライブラリによるUIで「相棒（ペット）」を表示。タスクを完了するごとに経験値が貯まり、ガチャで新しいスキル（ツール）やスキンを解放できるゲーミフィケーション要素。

## 3. 開発アプローチと制約 (Constraints)
- **環境**: Python 3.12, `uv` パッケージマネージャ, Mac M4 Pro。
- **リポジトリパス**: `/Users/gon9a/Library/CloudStorage/GoogleDrive-gon9a.chan@gmail.com/マイドライブ/workspace/claude-code-clone` (予定)
- **ステップアップ方式**: 序盤（Week 1-2）は確実な実装のため OpenAI API (GPT-4o-mini 等) を使用し、後半（Week 3-4）で Ollama 等を用いたローカルLLMへの移行（またはハイブリッド化）を行います。
- **ガバナンス (Human-in-the-Loop)**: 破壊的コマンドの実行前には必ずユーザーの承認を求めるUXを維持します。

---

## 4. 30日間のロードマップ (Phase Roadmap)

### Week 1: 基礎CLIとCoordinator Mode（基盤構築）
- **Day 1-2**: `uv` によるプロジェクト初期化。Typer/Richを用いたリッチなCLIフロントエンドの実装。
- **Day 3-5**: OpenAI APIを組み込んだ基本のAgentic Loop（Tool Callingによるファイル読み書き、コマンド実行）の実装。
- **Day 6-7**: **Coordinator Mode** の基礎実装。入力を受けてSub-agent（Searcher/Executor等）へ処理を振り分けるRouterの構築。

### Week 2: 深い思考と常時監視（ULTRAPLAN & KAIROS）
- **Day 8-10**: **ULTRAPLAN** の実装。非同期処理を活用し、バックグラウンドでループを回しながら、中間報告だけをCLIに表示する「長時間思考アーキテクチャ」の構築。
- **Day 11-14**: **KAIROS** の実装。ファイルシステムの監視（`watchdog`）やターミナルログのtailを行い、特定のトリガーで自律的に提案を行うデーモンプロセスの開発。

### Week 3: 愛着と記憶（BUDDY & Dream System）
- **Day 15-17**: **BUDDY** の実装。CLI画面の端にステータス（機嫌、経験値）を表示し、タスク完了時に「ガチャ」演出でプロンプトの追加コンテキスト（新スキル）を解放する仕組み。
- **Day 18-21**: **Dream System** の実装。対話ログを解析し、「ユーザーのコーディングの癖」や「よく間違えるコマンド」を抽出し、次回以降のシステムプロンプトに反映するバッチ処理の開発。

### Week 4: ローカルAI化とEvaluation UX（完成とチューニング）
- **Day 22-25**: **Local AI Integration**。Mac M4 Pro上で Ollama 等を立ち上げ、単純な処理（KAIROSの監視判定やDream Systemの要約）をローカルLLMにオフロードするハイブリッド構成の実装。
- **Day 26-28**: プロンプトエンジニアリング。ローカルLLMでもTool Callingが安定して動作するためのScaffolding（JSONスキーマ制約など）の調整。
- **Day 29-30**: **Evaluation UX**。開発したエージェントの性能（タスク成功率や消費コスト）を可視化する簡単な評価ダッシュボード（Streamlit）の作成と、総仕上げ。
