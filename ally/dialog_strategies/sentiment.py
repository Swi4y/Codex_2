from __future__ import annotations

from ally.dialog_strategies.base import Strategy
from ally.types import Reply, Sentiment

POS_Q = ["Что вас радует?", "Как сохранить этот настрой?"]
NEG_Q = ["Что могло бы поддержать вас?", "Есть ли маленький шаг вперед?"]
NEU_Q = ["Что вы замечаете?", "Что бы вы хотели исследовать?"]


class SentimentStrategy:
    def ask(self, *, threads: list[str], sentiment: Sentiment, history: list[dict]) -> Reply:
        pool = {
            "pos": POS_Q,
            "neg": NEG_Q,
            "neu": NEU_Q,
        }[sentiment]
        question = pool[len(history) % len(pool)]
        return Reply(threads=threads, question=question)


def create() -> Strategy:
    return SentimentStrategy()
