from __future__ import annotations

import html
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ally.service import core as service


def create_app(path: str | Path) -> FastAPI:
    data_path = Path(path)
    app = FastAPI()
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        entries = service.list_entries(data_path, limit=10)
        return templates.TemplateResponse("index.html", {"request": request, "entries": entries})

    @app.post("/", response_class=HTMLResponse)
    def write_entry(
        request: Request,
        text: str = Form(...),
        dialog: str = Form("static"),
        style: str = Form("gentle"),
    ) -> HTMLResponse:
        _, reply = service.create_entry(text=text, dialog=dialog, style=style, path=data_path)
        entries = service.list_entries(data_path, limit=10)
        return templates.TemplateResponse(
            "index.html", {"request": request, "entries": entries, "reply": reply}
        )

    @app.get("/entries/{entry_id}", response_class=HTMLResponse)
    def show_entry(request: Request, entry_id: str) -> HTMLResponse:
        meta, text = service.get_storage(data_path).get_entry(entry_id)
        return templates.TemplateResponse(
            "entry.html",
            {
                "request": request,
                "meta": meta,
                "text": html.escape(text).replace("\n", "<br>")
            },
        )

    @app.get("/pulse", response_class=HTMLResponse)
    def pulse_view(request: Request) -> HTMLResponse:
        data = service.pulse(data_path)
        return templates.TemplateResponse("pulse.html", {"request": request, "data": data})

    return app
