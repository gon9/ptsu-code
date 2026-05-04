"""LLM コスト推定テーブル。

料金は USD / 1M トークン。Ollama はローカル実行のためゼロ。
"""

COST_TABLE: dict[str, dict[str, float]] = {
    "gpt-5-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-haiku-3-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-3-7": {"input": 3.00, "output": 15.00},
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
}

_OLLAMA_PREFIXES = ("llama", "mistral", "gemma", "qwen", "phi", "deepseek")


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """モデル名とトークン数からコスト (USD) を推定する。

    Args:
        model: モデル名
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数

    Returns:
        推定コスト (USD)。Ollama など未知のローカルモデルは 0.0。
    """
    if any(model.lower().startswith(p) for p in _OLLAMA_PREFIXES):
        return 0.0

    rates = COST_TABLE.get(model, {"input": 0.0, "output": 0.0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def estimate_tokens_from_text(text: str) -> int:
    """テキスト文字数からトークン数を粗く推定する。

    英語は約 4 文字 / token、日本語は約 2 文字 / token を混合想定で
    簡易的に 3 文字 / token として計算する。

    Args:
        text: 対象テキスト

    Returns:
        推定トークン数
    """
    return max(1, len(text) // 3)
