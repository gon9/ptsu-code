"""LLM プロバイダーの可用性プローバー。

CLI 起動時に全プロバイダーの利用可否を一括チェックし、
セッション内で参照可能な AvailableProviders を生成する。
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ptsu_code.config import get_model, settings


@dataclass(frozen=True)
class ProviderAvailability:
    """プロバイダー 1 件の可用性情報。"""

    name: str
    available: bool
    model: str | None
    reason: str | None = None

    def __str__(self) -> str:
        """人間が読みやすい表現を返す。"""
        mark = "✓" if self.available else "✗"
        model_part = f"  {self.model}" if self.model else ""
        reason_part = f"  ({self.reason})" if self.reason else ""
        return f"{mark} {self.name:<12}{model_part}{reason_part}"


@dataclass
class AvailableProviders:
    """プローブ結果を保持し、セッション中に参照されるコンテナ。"""

    results: list[ProviderAvailability]

    def is_available(self, name: str) -> bool:
        """指定プロバイダーが利用可能かどうかを返す。

        Args:
            name: プロバイダー名

        Returns:
            利用可能なら True
        """
        return any(r.name == name and r.available for r in self.results)

    def best_for_memory(self, preferred: str) -> str:
        """メモリ抽出に最適なプロバイダー名を返す。

        preferred が利用可能ならそれを返す。
        利用不可なら available な最初のプロバイダーにフォールバックする。

        Args:
            preferred: 優先プロバイダー名

        Returns:
            利用可能なプロバイダー名
        """
        if self.is_available(preferred):
            return preferred
        for r in self.results:
            if r.available:
                return r.name
        return preferred

    def available_names(self) -> list[str]:
        """利用可能なプロバイダー名の一覧を返す。"""
        return [r.name for r in self.results if r.available]


def _check_ollama(base_url: str, timeout: float = 2.0) -> bool:
    """Ollama サーバーに HTTP GET で疎通確認する。

    Args:
        base_url: Ollama API ベース URL ("http://localhost:11434/v1")
        timeout: タイムアウト秒数

    Returns:
        接続可能なら True
    """
    health_url = base_url.rstrip("/").removesuffix("/v1").rstrip("/") + "/"
    try:
        httpx.get(health_url, timeout=timeout)
        return True
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
        return False


def probe_providers() -> AvailableProviders:
    """全プロバイダーの可用性をチェックして AvailableProviders を返す。

    Returns:
        プローブ結果
    """
    results: list[ProviderAvailability] = []

    # OpenAI
    if settings.openai_api_key:
        results.append(ProviderAvailability(
            name="openai",
            available=True,
            model=get_model("openai", "smart"),
        ))
    else:
        results.append(ProviderAvailability(
            name="openai",
            available=False,
            model=None,
            reason="PTSU_OPENAI_API_KEY not set",
        ))

    # Anthropic
    if settings.anthropic_api_key:
        results.append(ProviderAvailability(
            name="anthropic",
            available=True,
            model=get_model("anthropic", "smart"),
        ))
    else:
        results.append(ProviderAvailability(
            name="anthropic",
            available=False,
            model=None,
            reason="PTSU_ANTHROPIC_API_KEY not set",
        ))

    # Ollama (HTTP ping)
    ollama_ok = _check_ollama(settings.ollama_base_url)
    if ollama_ok:
        results.append(ProviderAvailability(
            name="ollama",
            available=True,
            model=f"{get_model('ollama', 'fast')} @ {settings.ollama_base_url}",
        ))
    else:
        results.append(ProviderAvailability(
            name="ollama",
            available=False,
            model=None,
            reason=f"not reachable at {settings.ollama_base_url}",
        ))

    return AvailableProviders(results=results)
