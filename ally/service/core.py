from __future__ import annotations

from pathlib import Path
from typing import Tuple

from ally.analysis.core import analyze_sentiment, top_terms
from ally.responder.core import respond
from ally.storage.file_store import FileStorage
from ally.types import EntryMeta


def get_storage(path: str | Path) -> FileStorage:
    return FileStorage(Path(path))


def init_storage(path: str | Path) -> None:
    get_storage(path).init()


def create_entry(
    *, text: str, dialog: str, style: str, path: str | Path
) -> Tuple[EntryMeta, str]:
    storage = get_storage(path)
    threads = top_terms(text)
    sentiment = analyze_sentiment(text)
    all_entries = storage.list_entries()
    history = [
        m for m in all_entries[-3:] if set(m.get("threads", [])) & set(threads)
    ]
    meta = storage.create_entry(
        text=text, threads=threads, sentiment=sentiment, style=style, dialog=dialog
    )
    reply = respond(
        dialog=dialog,
        style=style,
        threads=threads,
        sentiment=sentiment,
        history=history,
    )
    return meta, reply


def list_entries(path: str | Path, limit: int = 10) -> list[EntryMeta]:
    entries = get_storage(path).list_entries()
    entries.sort(key=lambda m: m["ts_utc"], reverse=True)
    return entries[:limit]


def threads(path: str | Path) -> dict[str, int]:
    return get_storage(path).threads_summary()


def pulse(path: str | Path) -> dict[str, dict[str, int]]:
    return get_storage(path).pulse()


def export(fmt: str, out: Path, path: str | Path) -> None:
    get_storage(path).export(fmt, out)
