from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from ally.service import init_storage, list_entries
from ally.web.app import create_app


def test_web_endpoints() -> None:
    with TemporaryDirectory() as d:
        init_storage(d)
        app = create_app(d)
        client = TestClient(app)
        r = client.post("/", data={"text": "хороший день", "dialog": "static", "style": "gentle"})
        assert r.status_code == 200
        entry_id = list_entries(d, limit=1)[0]["id"]
        r = client.get(f"/entries/{entry_id}")
        assert r.status_code == 200
        r = client.get("/pulse")
        assert r.status_code == 200
