#!/bin/bash
# E2E テストシナリオ実行スクリプト

echo "=== E2E Evaluation Test ==="
echo ""

# APIキーチェック
if [ -z "$PTSU_OPENAI_API_KEY" ]; then
    echo "❌ PTSU_OPENAI_API_KEY が設定されていません"
    echo "export PTSU_OPENAI_API_KEY=your-key を実行してください"
    exit 1
fi

echo "✓ OpenAI API Key: 設定済み"
echo ""

# シナリオ1: コードベース理解（自動テスト）
echo "=== シナリオ1: コードベース理解 ==="
echo "質問: このプロジェクトの構成を教えて"
echo ""

# 非対話モードでテスト（echoでパイプ）
echo "このプロジェクトの構成を教えて" | timeout 60 uv run ptsu chat --llm 2>&1 | tee /tmp/ptsu_test_scenario1.log

echo ""
echo "ログ保存: /tmp/ptsu_test_scenario1.log"
echo ""

# 結果確認
if grep -q "read_file\|execute_command" /tmp/ptsu_test_scenario1.log; then
    echo "✓ ツールが使用されました"
else
    echo "⚠ ツールが使用されていない可能性があります"
fi

echo ""
echo "=== テスト完了 ==="
echo "詳細ログを確認してください: /tmp/ptsu_test_scenario1.log"
