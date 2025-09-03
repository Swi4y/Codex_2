from __future__ import annotations

from itertools import cycle

from ally.dialog_strategies.base import Strategy
from ally.types import Reply, Sentiment

QUESTIONS = [
    "Что это для вас значит?",
    "Как вы хотите ответить на это?",
]
ESCALATION = "Вы часто возвращаетесь к теме {topic}. Что бы вы хотели изменить?"


class RulesStrategy:
    def __init__(self) -> None:
        self._rotator = cycle(QUESTIONS)

    def ask(self, *, threads: list[str], sentiment: Sentiment, history: list[dict]) -> Reply:
        topic = ""
        for t in threads:
            if any(t in m.get("threads", []) for m in history):
                topic = t
                break
        question = next(self._rotator)
        if topic:
            count = sum(1 for m in history if topic in m.get("threads", []))
            if count >= 1:
                question = ESCALATION.format(topic=topic)
        return Reply(threads=threads, question=question)


def create() -> Strategy:
    return RulesStrategy()
