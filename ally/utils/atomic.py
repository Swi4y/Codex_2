from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def _atomic_replace(tmp: NamedTemporaryFile, path: Path) -> None:
    tmp.flush()
    os.fsync(tmp.fileno())
    tmp.close()
    os.replace(tmp.name, path)


def atomic_write_json(path: str | Path, obj: Any) -> None:
    """Atomically write JSON to ``path``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        json.dump(obj, tmp, ensure_ascii=False)
        _atomic_replace(tmp, target)


def atomic_append_jsonl(path: str | Path, obj: Any) -> None:
    """Atomically append a JSON line to ``path``."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        if target.exists():
            with target.open("r", encoding="utf-8") as src:
                tmp.write(src.read())
        tmp.write(line)
        _atomic_replace(tmp, target)
