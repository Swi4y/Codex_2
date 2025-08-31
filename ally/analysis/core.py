import re
from collections import Counter
from typing import Iterable, List

RU_STOP = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как",
    "а", "то", "все", "она", "так", "его", "но", "да", "ты", "к",
}
EN_STOP = {
    "the", "and", "to", "of", "in", "a", "is", "it", "that", "i",
    "you", "for", "on", "with", "as", "at", "this", "but", "be", "are",
}
STOPWORDS = RU_STOP | EN_STOP


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[\w']+", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def top_terms(tokens: Iterable[str], n: int = 3) -> List[str]:
    counts = Counter(tokens)
    return [t for t, _ in counts.most_common(n)]
