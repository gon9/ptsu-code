"""Session Memory の LLM 抽出ロジック。

Claude Code の SessionMemory forked agent 相当の機能を
シンプルなワンショット LLM 呼び出しで実現する。
"""

import logging
from typing import Any

from ptsu_code.agent.providers.base import LLMProvider
from ptsu_code.memory.template import DEFAULT_TEMPLATE, has_required_sections

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """You are a session notes extractor for a coding assistant.
Your task is to update structured session notes based on the conversation history.

CRITICAL RULES — follow these exactly:
1. Preserve ALL section headers (lines starting with #) EXACTLY as they appear — do not add, remove, or rename them
2. Preserve ALL italic _description_ lines (lines in the format `_..._` immediately after headers) EXACTLY
3. Only update/add content BELOW the italic description lines in each section
4. Write information-dense, specific content (file paths, function names, commands, error messages, exact values)
5. Keep each section under approximately 2000 tokens
6. Keep total output under approximately 12000 tokens
7. Do NOT mention or reference this note-taking process anywhere in the content
8. Leave sections empty if no relevant new information exists for them
9. Output ONLY the complete updated markdown file — no explanations, no preamble, no code fences
"""


class MemoryExtractor:
    """会話から Session Memory を LLM で抽出するクラス。"""

    def __init__(self, provider: LLMProvider) -> None:
        """初期化。

        Args:
            provider: LLM プロバイダー
        """
        self.provider = provider

    def extract(
        self,
        conversation: list[dict[str, str]],
        current_memory: str,
    ) -> str:
        """会話から Session Memory を更新する。

        Args:
            conversation: 会話履歴。各要素は {"user": str, "assistant": str}
            current_memory: 現在のメモリ内容

        Returns:
            更新されたメモリ内容。抽出失敗時は current_memory を返す

        Raises:
            ValueError: 会話が空の場合
        """
        if not conversation:
            raise ValueError("conversation is empty")

        messages = self._build_messages(conversation, current_memory)

        try:
            response = self.provider.chat(messages=messages, temperature=0.0)
            extracted = response.content.strip()

            if not extracted:
                logger.warning("Memory extraction returned empty content — keeping current")
                return current_memory

            if not has_required_sections(extracted):
                logger.warning(
                    "Extracted memory missing required sections — keeping current"
                )
                return current_memory

            return extracted

        except Exception:
            logger.exception("Memory extraction failed — keeping current memory")
            return current_memory

    def _build_messages(
        self,
        conversation: list[dict[str, str]],
        current_memory: str,
    ) -> list[dict[str, Any]]:
        """LLM に渡すメッセージリストを構築する。

        Args:
            conversation: 会話履歴
            current_memory: 現在のメモリ内容

        Returns:
            OpenAI 互換メッセージリスト
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
        ]

        for turn in conversation:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})

        current_notes = current_memory if current_memory.strip() else DEFAULT_TEMPLATE
        extraction_request = (
            f"Current session notes:\n\n{current_notes}\n\n"
            "Update the session notes based on the conversation above. "
            "Output only the complete updated markdown."
        )
        messages.append({"role": "user", "content": extraction_request})

        return messages
