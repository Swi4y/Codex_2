from __future__ import annotations

from typing import Protocol

from ally.types import Reply, Sentiment


class Strategy(Protocol):
    """Protocol for dialog strategies."""

    def ask(self, *, threads: list[str], sentiment: Sentiment, history: list[dict]) -> Reply:
        ...
