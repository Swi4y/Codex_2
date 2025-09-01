from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict

Sentiment = Literal["pos", "neg", "neu"]


class EntryMeta(TypedDict):
    """Metadata stored for each diary entry."""

    id: str
    ts_utc: str
    text: str
    threads: List[str]
    sentiment: Sentiment
    style: str
    dialog: str


class Reply(TypedDict, total=False):
    """Reply returned by dialog strategies."""

    threads: List[str]
    question: str
    step: Optional[str]
