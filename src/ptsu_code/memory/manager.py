"""Session Memory Manager。

Dream System のメインオーケストレーター。
state / storage / triggers / extractor を統合し、
CLI から呼び出せるシンプルな API を提供する。
"""

import logging
from pathlib import Path

from ptsu_code.agent.providers.base import LLMProvider
from ptsu_code.memory.extractor import MemoryExtractor
from ptsu_code.memory.models import SessionMemoryConfig, SessionMemoryState
from ptsu_code.memory.storage import SessionMemoryStorage
from ptsu_code.memory.template import is_empty
from ptsu_code.memory.triggers import should_extract

logger = logging.getLogger(__name__)


class SessionMemoryManager:
    """Session Memory の統合マネージャー。

    使い方:
        manager = SessionMemoryManager(provider, session_id, data_dir)

        # 起動時: 前回メモリを取得して system prompt に注入
        prev = manager.load_previous()
        if prev:
            session.add_message("system", f"## Previous Session Memory\\n{prev}")

        # 各ターン後
        manager.add_turn(user_input, response, tool_call_count)
        manager.maybe_extract()

        # 終了時
        manager.finalize()
    """

    def __init__(
        self,
        provider: LLMProvider,
        session_id: str,
        data_dir: Path,
        config: SessionMemoryConfig | None = None,
    ) -> None:
        """初期化。

        Args:
            provider: LLM プロバイダー（メモリ抽出に使用）
            session_id: セッション識別子（例: 20260429_120000）
            data_dir: データ保存ルートディレクトリ（例: ~/.ptsu）
            config: Session Memory の設定（デフォルトは SessionMemoryConfig()）
        """
        self.config = config or SessionMemoryConfig()
        self.state = SessionMemoryState()
        self.storage = SessionMemoryStorage(data_dir, session_id)
        self.extractor = MemoryExtractor(provider)
        self._extraction_count = 0

    def add_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        tool_call_count: int = 0,
    ) -> None:
        """1ターン分のデータを追加する。

        Args:
            user_msg: ユーザーメッセージ
            assistant_msg: アシスタントの応答
            tool_call_count: このターンのツール呼び出し数
        """
        self.state.add_turn(user_msg, assistant_msg, tool_call_count)

    def maybe_extract(self) -> bool:
        """条件が満たされれば Session Memory を抽出・保存する。

        Returns:
            抽出を実行した場合は True、スキップした場合は False
        """
        if not should_extract(self.state, self.config):
            return False

        return self._do_extract()

    def force_extract(self) -> bool:
        """会話があれば即座に Session Memory を抽出・保存する。

        /summary コマンドや終了時の finalize から呼ばれる。

        Returns:
            抽出を実行した場合は True、会話がなければ False
        """
        if not self.state.conversation:
            logger.debug("force_extract: no conversation to extract")
            return False

        return self._do_extract()

    def load_previous(self) -> str | None:
        """前回セッションのメモリを読み込む。

        ファイルが存在しない、またはテンプレートのみの場合は None を返す。

        Returns:
            前回のメモリ内容、または None
        """
        if not self.storage.exists():
            return None

        content = self.storage.load()
        if is_empty(content):
            return None

        return content

    def finalize(self) -> None:
        """セッション終了時の処理。

        残りの会話を抽出してアーカイブに保存する。
        """
        if self.state.conversation:
            self._do_extract()

        archived = self.storage.archive()
        if archived:
            logger.info("Session memory archived: %s", archived)

    @property
    def extraction_count(self) -> int:
        """今セッションで抽出を実行した回数。"""
        return self._extraction_count

    def _do_extract(self) -> bool:
        """実際の抽出処理。

        Returns:
            成功した場合は True
        """
        current_memory = self.storage.load()
        logger.debug(
            "Extracting session memory (turn %d, extraction #%d)",
            len(self.state.conversation),
            self._extraction_count + 1,
        )

        new_memory = self.extractor.extract(
            conversation=self.state.conversation,
            current_memory=current_memory,
        )

        if new_memory == current_memory and not is_empty(current_memory):
            logger.debug("Memory extraction produced no change — skipping save")
        else:
            self.storage.save(new_memory)

        self.state.record_extraction()
        self._extraction_count += 1
        return True
