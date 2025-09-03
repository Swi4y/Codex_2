from __future__ import annotations

import re
from collections import Counter
from typing import List

RU_STOP = {
    "и",
    "в",
    "не",
    "на",
    "я",
    "это",
    "что",
    "но",
    "а",
}

EN_STOP = {
    "the",
    "and",
    "to",
    "of",
    "a",
    "in",
    "is",
    "it",
    "that",
    "i",
}

POSITIVE = {"хорошо", "прекрасно", "отлично", "happy", "great", "good"}
NEGATIVE = {"плохо", "ужасно", "плохой", "bad", "sad", "terrible"}
TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    """Tokenize ``text`` keeping hyphenated words as single tokens."""
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    filtered = [t for t in tokens if t not in RU_STOP and t not in EN_STOP]
    return filtered


def top_terms(text: str, k: int = 3) -> List[str]:
    tokens = tokenize(text)
    if not tokens:
        return []
    counts = Counter(tokens)
    return [t for t, _ in counts.most_common(k)]


def analyze_sentiment(text: str) -> str:
    tokens = tokenize(text)
    pos = sum(1 for t in tokens if t in POSITIVE)
    neg = sum(1 for t in tokens if t in NEGATIVE)
    if pos > neg:
        return "pos"
    if neg > pos:
        return "neg"
    return "neu"
