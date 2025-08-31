import json
from collections import Counter
from datetime import datetime
from typing import Dict, List

from ..analysis import tokenize, top_terms
from ..responder import respond
from ..storage import get_storage


def _audit(log_path: str, entry_id: int | None, actions: List[str]):
    record = {
        "timestamp": datetime.now().isoformat(),
        "entry_id": entry_id,
        "actions": actions,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def init_storage(kind: str, path: str, log_path: str):
    storage = get_storage(kind, path)
    storage.init()
    _audit(log_path, None, ["init"])
    return storage


def write_entry(kind: str, path: str, log_path: str, text: str, style: str = "gentle") -> str:
    storage = get_storage(kind, path)
    storage.init()
    tokens = tokenize(text)
    terms = top_terms(tokens) or ["разное"]
    ts = datetime.now().isoformat()
    entry = storage.add_entry(text, terms, ts)
    _audit(log_path, entry["id"], ["write"])
    return respond(terms, style)


def list_entries(kind: str, path: str, limit: int = 10) -> List[Dict]:
    storage = get_storage(kind, path)
    storage.init()
    return storage.list_entries(limit)


def list_threads(kind: str, path: str) -> Dict[str, int]:
    storage = get_storage(kind, path)
    storage.init()
    return storage.get_threads()


def pulse(kind: str, path: str) -> Dict[str, int]:
    storage = get_storage(kind, path)
    storage.init()
    entries = storage.all_entries()
    tokens: List[str] = []
    for e in entries:
        tokens.extend(tokenize(e["text"]))
    counts = Counter(tokens)
    return dict(counts.most_common(10))


def export_entries(kind: str, path: str, fmt: str, out_path: str, log_path: str):
    storage = get_storage(kind, path)
    storage.init()
    entries = storage.all_entries()
    if fmt == "json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            for e in entries:
                threads = ", ".join(e.get("threads", []))
                f.write(f"## {e['timestamp']} ({threads})\n\n{e['text']}\n\n")
    _audit(log_path, None, ["export", fmt, out_path])
