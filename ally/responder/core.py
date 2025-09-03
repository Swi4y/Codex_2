from __future__ import annotations

from typing import Callable, Dict, List

from ally.dialog_strategies import rules, sentiment, static
from ally.types import Reply, Sentiment

STRATEGY_FACTORIES: Dict[str, Callable[[], object]] = {
    "static": static.create,
    "rules": rules.create,
    "sentiment": sentiment.create,
}

STYLES = {
    "gentle": {"step": "сделайте небольшой вдох"},
    "skeptic": {"step": "какой факт вы упускаете?"},
    "poet": {"step": "найдите метафору дня"},
}


def format_reply(reply: Reply) -> str:
    parts: List[str] = []
    if reply.get("threads"):
        parts.append("нити: " + ", ".join(reply["threads"]))
    parts.append(f"вопрос: {reply['question']}")
    if reply.get("step"):
        parts.append(f"маленький шаг: {reply['step']}")
    return "\n\n".join(parts)


def respond(
    *,
    dialog: str,
    style: str,
    threads: list[str],
    sentiment: Sentiment,
    history: list[dict],
) -> str:
    factory = STRATEGY_FACTORIES.get(dialog, static.create)
    strategy = factory()
    reply = strategy.ask(threads=threads, sentiment=sentiment, history=history)
    style_cfg = STYLES.get(style)
    if style_cfg and "step" not in reply and style_cfg.get("step"):
        reply["step"] = style_cfg["step"]
    return format_reply(reply)
