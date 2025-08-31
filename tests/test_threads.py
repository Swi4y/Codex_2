import os
import tempfile

from ally.service import init_storage, list_threads, write_entry


def test_write_creates_thread():
    with tempfile.TemporaryDirectory() as tmp:
        kind = "files"
        log = os.path.join(tmp, "audit.jsonl")
        init_storage(kind, tmp, log)
        write_entry(kind, tmp, log, "Сегодня я гулял в парке", "gentle")
        threads = list_threads(kind, tmp)
        assert threads
