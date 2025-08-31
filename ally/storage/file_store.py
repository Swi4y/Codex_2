import json
import os
from typing import Dict, List


class FileStorage:
    def __init__(self, path: str = "data_files"):
        self.path = path
        self.entries_dir = os.path.join(self.path, "entries")
        self.meta_file = os.path.join(self.path, "meta.jsonl")
        self.threads_file = os.path.join(self.path, "threads.json")

    def init(self):
        os.makedirs(self.entries_dir, exist_ok=True)
        if not os.path.exists(self.meta_file):
            open(self.meta_file, "w").close()
        if not os.path.exists(self.threads_file):
            with open(self.threads_file, "w") as f:
                json.dump({}, f)

    def _next_id(self) -> int:
        if not os.path.exists(self.meta_file):
            return 1
        with open(self.meta_file, "r") as f:
            return sum(1 for _ in f) + 1

    def add_entry(self, text: str, threads: List[str], timestamp: str) -> Dict:
        eid = self._next_id()
        with open(os.path.join(self.entries_dir, f"{eid}.md"), "w", encoding="utf-8") as f:
            f.write(text)
        meta = {"id": eid, "timestamp": timestamp, "threads": threads}
        with open(self.meta_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        if os.path.exists(self.threads_file):
            with open(self.threads_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        for t in threads:
            data[t] = data.get(t, 0) + 1
        with open(self.threads_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        meta["text"] = text
        return meta

    def list_entries(self, limit: int = 10) -> List[Dict]:
        if not os.path.exists(self.meta_file):
            return []
        with open(self.meta_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        result = []
        for line in reversed(lines[-limit:]):
            meta = json.loads(line)
            eid = meta["id"]
            with open(os.path.join(self.entries_dir, f"{eid}.md"), "r", encoding="utf-8") as f:
                text = f.read()
            meta["text"] = text
            result.append(meta)
        return result

    def get_threads(self) -> Dict[str, int]:
        if not os.path.exists(self.threads_file):
            return {}
        with open(self.threads_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def all_entries(self) -> List[Dict]:
        if not os.path.exists(self.meta_file):
            return []
        with open(self.meta_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        result = []
        for line in lines:
            meta = json.loads(line)
            eid = meta["id"]
            with open(os.path.join(self.entries_dir, f"{eid}.md"), "r", encoding="utf-8") as f:
                text = f.read()
            meta["text"] = text
            result.append(meta)
        return result
