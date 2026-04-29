"""Session Memory パッケージ。

Dream System の実体。セッション中の会話から重要情報を自動抽出し、
次回セッション起動時に system prompt へ注入することで学習効果を実現する。
"""

from ptsu_code.memory.manager import SessionMemoryManager

__all__ = ["SessionMemoryManager"]
