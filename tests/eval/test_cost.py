"""eval/cost.py のユニットテスト。"""

import pytest

from ptsu_code.eval.cost import estimate_cost, estimate_tokens_from_text


class TestEstimateCost:
    """estimate_cost のテスト。"""

    def test_known_model_returns_nonzero(self) -> None:
        """既知モデルはゼロより大きいコストを返す。"""
        cost = estimate_cost("gpt-4o", 1_000_000, 0)
        assert cost == pytest.approx(2.50, rel=1e-3)

    def test_output_tokens_are_more_expensive(self) -> None:
        """出力トークンの単価が入力より高い（gpt-4o）。"""
        cost_in = estimate_cost("gpt-4o", 1_000_000, 0)
        cost_out = estimate_cost("gpt-4o", 0, 1_000_000)
        assert cost_out > cost_in

    def test_ollama_llama_is_zero(self) -> None:
        """Ollama モデル (llama prefix) はコストゼロ。"""
        assert estimate_cost("llama3.2", 100_000, 100_000) == 0.0

    def test_unknown_model_is_zero(self) -> None:
        """未知モデルはコストゼロ。"""
        assert estimate_cost("unknown-model-xyz", 100_000, 100_000) == 0.0

    def test_zero_tokens_is_zero(self) -> None:
        """トークンゼロはコストゼロ。"""
        assert estimate_cost("gpt-4o", 0, 0) == 0.0

    def test_gpt5_mini(self) -> None:
        """gpt-5-mini のコスト計算が正しい。"""
        cost = estimate_cost("gpt-5-mini", 1_000_000, 1_000_000)
        assert cost == pytest.approx(0.15 + 0.60, rel=1e-3)


class TestEstimateTokensFromText:
    """estimate_tokens_from_text のテスト。"""

    def test_empty_string_returns_one(self) -> None:
        """空文字は最小値 1 を返す。"""
        assert estimate_tokens_from_text("") == 1

    def test_longer_text_returns_more_tokens(self) -> None:
        """長いテキストほど多くのトークンを返す。"""
        short = estimate_tokens_from_text("hello")
        long = estimate_tokens_from_text("hello " * 100)
        assert long > short

    def test_returns_positive(self) -> None:
        """常に正の値を返す。"""
        assert estimate_tokens_from_text("a") >= 1
