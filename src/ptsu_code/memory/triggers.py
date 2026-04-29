"""Session Memory の抽出トリガーロジック。

Claude Code の shouldExtractMemory に相当するモジュール。
"""

from ptsu_code.memory.models import SessionMemoryConfig, SessionMemoryState


def estimate_tokens(text: str) -> int:
    """テキストのトークン数を概算する。

    Claude Code の roughTokenCountEstimation と同様の手法。
    4文字 ≒ 1トークンとして概算する。

    Args:
        text: トークン数を推定するテキスト

    Returns:
        推定トークン数
    """
    return len(text) // 4


def should_extract(state: SessionMemoryState, config: SessionMemoryConfig) -> bool:
    """現在の状態に基づいて Session Memory を抽出すべきか判定する。

    判定ルール:
    - 初期化されていない場合: 会話の総トークン数が minimum_tokens_to_init を超えたら初期化
    - 初期化済みの場合: 以下のいずれかを満たしたら抽出
        1. tokens_since_last >= minimum_tokens_between_update
           AND tool_calls_since_last >= tool_calls_between_updates
        2. tokens_since_last >= minimum_tokens_between_update
           AND 会話ターン数が 1 以上ある（最後のターンにツールコールなし相当）

    Args:
        state: 現在のセッション状態
        config: Session Memory の設定

    Returns:
        抽出を実行すべき場合は True
    """
    if not state.conversation:
        return False

    total_tokens = state.total_chars() // 4

    if not state.initialized:
        if total_tokens < config.minimum_tokens_to_init:
            return False
        state.initialized = True

    tokens_since_last = state.chars_since_last_extraction() // 4
    has_met_token_threshold = tokens_since_last >= config.minimum_tokens_between_update
    has_met_tool_call_threshold = (
        state.tool_calls_since_last_extraction >= config.tool_calls_between_updates
    )

    return has_met_token_threshold and (
        has_met_tool_call_threshold or len(state.conversation) > 0
    )
