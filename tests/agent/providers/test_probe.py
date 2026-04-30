"""ProviderProber のユニットテスト。"""

from unittest.mock import patch

import httpx
import pytest

from ptsu_code.agent.providers.probe import (
    AvailableProviders,
    ProviderAvailability,
    _check_ollama,
    probe_providers,
)


class TestProviderAvailability:
    """ProviderAvailability のテスト。"""

    def test_str_available(self) -> None:
        """利用可能なプロバイダーの文字列表現。"""
        pa = ProviderAvailability(name="openai", available=True, model="gpt-4o")
        s = str(pa)
        assert "✓" in s
        assert "openai" in s

    def test_str_unavailable(self) -> None:
        """利用不可のプロバイダーの文字列表現。"""
        pa = ProviderAvailability(
            name="ollama", available=False, model=None, reason="not reachable"
        )
        s = str(pa)
        assert "✗" in s
        assert "not reachable" in s


class TestAvailableProviders:
    """AvailableProviders のテスト。"""

    @pytest.fixture()
    def sample(self) -> AvailableProviders:
        """サンプルのプローブ結果。"""
        return AvailableProviders(results=[
            ProviderAvailability(name="openai", available=True, model="gpt-4o"),
            ProviderAvailability(name="anthropic", available=False, model=None, reason="no key"),
            ProviderAvailability(name="ollama", available=True, model="llama3.2"),
        ])

    def test_is_available_true(self, sample) -> None:
        """利用可能なプロバイダーは True を返す。"""
        assert sample.is_available("openai") is True
        assert sample.is_available("ollama") is True

    def test_is_available_false(self, sample) -> None:
        """利用不可のプロバイダーは False を返す。"""
        assert sample.is_available("anthropic") is False

    def test_is_available_unknown(self, sample) -> None:
        """未知のプロバイダーは False を返す。"""
        assert sample.is_available("unknown") is False

    def test_available_names(self, sample) -> None:
        """利用可能なプロバイダー名一覧が返る。"""
        assert sample.available_names() == ["openai", "ollama"]

    def test_best_for_memory_preferred_available(self, sample) -> None:
        """preferred が利用可能なら preferred を返す。"""
        assert sample.best_for_memory("ollama") == "ollama"

    def test_best_for_memory_preferred_unavailable(self, sample) -> None:
        """preferred が利用不可なら最初の利用可能なプロバイダーを返す。"""
        result = sample.best_for_memory("anthropic")
        assert result in sample.available_names()

    def test_best_for_memory_all_unavailable(self) -> None:
        """全て利用不可の場合は preferred をそのまま返す。"""
        av = AvailableProviders(results=[
            ProviderAvailability(name="openai", available=False, model=None),
        ])
        assert av.best_for_memory("openai") == "openai"


class TestCheckOllama:
    """_check_ollama のテスト。"""

    def test_returns_true_when_reachable(self) -> None:
        """到達可能な場合 True を返す。"""
        with patch("ptsu_code.agent.providers.probe.httpx.get") as mock_get:
            mock_get.return_value = None
            assert _check_ollama("http://localhost:11434/v1") is True

    def test_returns_false_on_connect_error(self) -> None:
        """接続エラーの場合 False を返す。"""
        with patch("ptsu_code.agent.providers.probe.httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("refused")
            assert _check_ollama("http://localhost:11434/v1") is False

    def test_returns_false_on_timeout(self) -> None:
        """タイムアウトの場合 False を返す。"""
        with patch("ptsu_code.agent.providers.probe.httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            assert _check_ollama("http://localhost:11434/v1") is False

    def test_strips_v1_from_url(self) -> None:
        """health check URL が /v1 を除いた root になること。"""
        with patch("ptsu_code.agent.providers.probe.httpx.get") as mock_get:
            mock_get.return_value = None
            _check_ollama("http://localhost:11434/v1")
            called_url = mock_get.call_args.args[0]
            assert called_url == "http://localhost:11434/"
            assert "/v1" not in called_url


class TestProbeProviders:
    """probe_providers のテスト。"""

    def test_returns_all_three_providers(self) -> None:
        """3 プロバイダー分の結果が返る。"""
        with patch("ptsu_code.agent.providers.probe._check_ollama", return_value=False), \
             patch("ptsu_code.agent.providers.probe.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = ""
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.openai_model_fast = "gpt-5-mini"
            mock_settings.openai_model_smart = "gpt-4o"
            mock_settings.anthropic_model_fast = "claude-haiku-4-5"
            mock_settings.anthropic_model_smart = "claude-sonnet-4-5"
            mock_settings.ollama_model_fast = "llama3.2"
            mock_settings.ollama_model_smart = "llama3.1"
            result = probe_providers()
        assert len(result.results) == 3
        names = [r.name for r in result.results]
        assert "openai" in names
        assert "anthropic" in names
        assert "ollama" in names

    def test_openai_available_when_key_set(self) -> None:
        """API キーがある場合 openai が利用可能。"""
        with patch("ptsu_code.agent.providers.probe._check_ollama", return_value=False), \
             patch("ptsu_code.agent.providers.probe.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test"
            mock_settings.anthropic_api_key = ""
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.openai_model_fast = "gpt-5-mini"
            mock_settings.openai_model_smart = "gpt-4o"
            mock_settings.anthropic_model_fast = "claude-haiku-4-5"
            mock_settings.anthropic_model_smart = "claude-sonnet-4-5"
            mock_settings.ollama_model_fast = "llama3.2"
            mock_settings.ollama_model_smart = "llama3.1"
            result = probe_providers()
        assert result.is_available("openai") is True
        assert result.is_available("anthropic") is False

    def test_ollama_available_when_reachable(self) -> None:
        """Ollama が起動中なら利用可能。"""
        with patch("ptsu_code.agent.providers.probe._check_ollama", return_value=True), \
             patch("ptsu_code.agent.providers.probe.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.openai_model_fast = "gpt-5-mini"
            mock_settings.openai_model_smart = "gpt-4o"
            mock_settings.anthropic_model_fast = "claude-haiku-4-5"
            mock_settings.anthropic_model_smart = "claude-sonnet-4-5"
            mock_settings.ollama_model_fast = "llama3.2"
            mock_settings.ollama_model_smart = "llama3.1"
            result = probe_providers()
        assert result.is_available("ollama") is True
