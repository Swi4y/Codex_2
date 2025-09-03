from __future__ import annotations

from ally.dialog_strategies.base import Strategy
from ally.types import Reply, Sentiment

STATIC_QUESTION = "Что бы вы хотели исследовать дальше?"


class StaticStrategy:
    """Return a fixed question regardless of input."""

    def ask(self, *, threads: list[str], sentiment: Sentiment, history: list[dict]) -> Reply:  # noqa: D401
        return Reply(threads=threads, question=STATIC_QUESTION)


def create() -> Strategy:
    return StaticStrategy()
