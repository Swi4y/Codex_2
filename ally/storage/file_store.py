from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from ally.types import EntryMeta
from ally.utils.atomic import atomic_append_jsonl, atomic_write_json


class FileStorage:
    """File-based storage for diary entries."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def init(self) -> None:
        (self.path / "entries").mkdir(parents=True, exist_ok=True)
        meta = self.path / "meta.jsonl"
        threads = self.path / "threads.json"
        if not meta.exists():
            meta.touch()
        if not threads.exists():
            atomic_write_json(threads, {})

    # internal helpers
    def _meta_file(self) -> Path:
        return self.path / "meta.jsonl"

    def _read_meta(self) -> List[EntryMeta]:
        entries: List[EntryMeta] = []
        mf = self._meta_file()
        if mf.exists():
            with mf.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        return entries

    # public API
    def create_entry(
        self, *, text: str, threads: List[str], sentiment: str, style: str, dialog: str
    ) -> EntryMeta:
        eid = uuid4().hex
        ts = datetime.now(timezone.utc).isoformat()
        dt = datetime.fromisoformat(ts)
        rel = Path("entries") / f"{dt.year:04d}" / f"{dt.month:02d}" / f"{dt.day:02d}"
        dir_path = self.path / rel
        dir_path.mkdir(parents=True, exist_ok=True)
        entry_path = dir_path / f"{eid}.md"
        entry_path.write_text(text, encoding="utf-8")
        meta: EntryMeta = {
            "id": eid,
            "ts_utc": ts,
            "text": text,
            "threads": threads,
            "sentiment": sentiment,
            "style": style,
            "dialog": dialog,
        }
        atomic_append_jsonl(self._meta_file(), meta)
        # update threads
        tpath = self.path / "threads.json"
        data: dict[str, int] = {}
        if tpath.exists():
            with tpath.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
        for t in threads:
            data[t] = data.get(t, 0) + 1
        atomic_write_json(tpath, data)
        return meta

    def list_entries(self) -> List[EntryMeta]:
        return self._read_meta()

    def get_entry(self, entry_id: str) -> tuple[EntryMeta, str]:
        entries = self._read_meta()
        for m in entries:
            if m["id"] == entry_id:
                dt = datetime.fromisoformat(m["ts_utc"])
                path = (
                    self.path
                    / "entries"
                    / f"{dt.year:04d}"
                    / f"{dt.month:02d}"
                    / f"{dt.day:02d}"
                    / f"{entry_id}.md"
                )
                text = path.read_text(encoding="utf-8")
                return m, text
        raise KeyError(entry_id)

    def threads_summary(self) -> dict[str, int]:
        tpath = self.path / "threads.json"
        if tpath.exists():
            with tpath.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def pulse(self) -> dict[str, dict[str, int]]:
        entries = self._read_meta()
        themes: dict[str, int] = {}
        days: dict[str, int] = {}
        sentiments: dict[str, int] = {}
        for m in entries:
            day = m["ts_utc"].split("T")[0]
            days[day] = days.get(day, 0) + 1
            sentiments[m["sentiment"]] = sentiments.get(m["sentiment"], 0) + 1
            for t in m["threads"]:
                themes[t] = themes.get(t, 0) + 1
        return {"themes": themes, "days": days, "sentiments": sentiments}

    def export(self, fmt: str, out: Path) -> None:
        entries = self._read_meta()
        if fmt == "json":
            out.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        if fmt == "md":
            lines: list[str] = []
            for m in entries:
                lines.append(f"## {m['ts_utc']}")
                if m["threads"]:
                    lines.append("нити: " + ", ".join(m["threads"]))
                lines.append(m["text"])
                lines.append("")
            out.write_text("\n".join(lines), encoding="utf-8")
            return
        if fmt == "html":
            body = []
            for m in entries:
                body.append(f"<h2>{m['ts_utc']}</h2><p>{m['text']}</p>")
            out.write_text(
                "<html><body>" + "".join(body) + "</body></html>", encoding="utf-8"
            )
            return
        raise ValueError("unknown format")
