"""コンテキスト管理 — Observation Masking。

JetBrains Research (2025-12) の手法に基づき、古いツール結果（observation）を
マスクすることで入力トークン数を抑制する。

参考: Lindenbauer et al., "Cutting Through the Noise: Smarter Context
Management for LLM-Powered Agents", JetBrains Research Blog, 2025.

設計方針:
  - role="tool" のメッセージのみマスク対象（observation）
  - role="assistant"（推論 + action）と role="user" は常に保持
  - 直近 keep_recent 個の tool メッセージは内容を保持
  - それ以外の tool メッセージは内容を短い要約に置換
"""

from typing import Any

_DEFAULT_KEEP_RECENT = 6


def mask_observations(
    messages: list[dict[str, Any]],
    keep_recent: int = _DEFAULT_KEEP_RECENT,
) -> list[dict[str, Any]]:
    """古いツール結果をマスクし、入力トークンを削減する。

    Args:
        messages: OpenAI互換形式のメッセージリスト
        keep_recent: 直近で保持するtoolメッセージ数

    Returns:
        マスク済みメッセージリスト（元のリストは変更しない）
    """
    tool_indices = [i for i, m in enumerate(messages) if m.get("role") == "tool"]

    if len(tool_indices) <= keep_recent:
        return messages

    mask_target = set(tool_indices[: len(tool_indices) - keep_recent])

    result: list[dict[str, Any]] = []
    for i, msg in enumerate(messages):
        if i in mask_target:
            tool_name = msg.get("name", "tool")
            original_len = len(msg.get("content", ""))
            result.append({
                **msg,
                "content": f"[Observation masked: {tool_name} ({original_len} chars)]",
            })
        else:
            result.append(msg)

    return result
