import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ally.utils import atomic_append_jsonl, atomic_write_json


def test_atomic_functions() -> None:
    with TemporaryDirectory() as d:
        p = Path(d) / "data.json"
        atomic_write_json(p, {"a": 1})
        assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1}
        l = Path(d) / "data.jsonl"
        atomic_append_jsonl(l, {"x": 1})
        atomic_append_jsonl(l, {"y": 2})
        lines = [json.loads(s) for s in l.read_text(encoding="utf-8").splitlines()]
        assert lines[0] == {"x": 1}
        assert lines[1] == {"y": 2}
