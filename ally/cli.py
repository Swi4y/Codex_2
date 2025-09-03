from __future__ import annotations

import json
import os
from pathlib import Path

import click
from rich.console import Console

from ally.service import core as service

console = Console()


def default_path() -> Path:
    return Path(os.environ.get("ALLY_DATA_PATH", "data"))


@click.group()
@click.option("--path", type=click.Path(), default=str(default_path()))
@click.pass_context
def cli(ctx: click.Context, path: str) -> None:
    """Разговорный дневник CLI."""
    ctx.obj = {"path": Path(path)}


@cli.command()
@click.pass_obj
def init(obj: dict) -> None:
    """Initialize storage."""
    service.init_storage(obj["path"])
    console.print("storage initialized", style="green")


@cli.command()
@click.argument("text")
@click.option("--dialog", default="static", type=click.Choice(["static", "rules", "sentiment"]))
@click.option("--style", default="gentle", type=click.Choice(["gentle", "skeptic", "poet"]))
@click.pass_obj
def write(obj: dict, text: str, dialog: str, style: str) -> None:
    """Add a diary entry."""
    meta, reply = service.create_entry(text=text, dialog=dialog, style=style, path=obj["path"])
    console.print(reply)


@cli.command(name="list")
@click.option("--limit", default=10, type=int)
@click.pass_obj
def list_entries(obj: dict, limit: int) -> None:
    entries = service.list_entries(obj["path"], limit)
    for m in entries:
        console.print(f"{m['id']} | {m['ts_utc']} | {', '.join(m['threads'])} | {m['sentiment']}")


@cli.command()
@click.pass_obj
def threads(obj: dict) -> None:
    data = service.threads(obj["path"])
    console.print(json.dumps(data, ensure_ascii=False))


@cli.command()
@click.pass_obj
def pulse(obj: dict) -> None:
    data = service.pulse(obj["path"])
    console.print(json.dumps(data, ensure_ascii=False))


@cli.command()
@click.option("--fmt", default="md", type=click.Choice(["md", "json", "html"]))
@click.option("--out", type=click.Path())
@click.pass_obj
def export(obj: dict, fmt: str, out: str | None) -> None:
    out_path = Path(out) if out else Path(f"export.{fmt}")
    service.export(fmt, out_path, obj["path"])
    console.print(f"exported to {out_path}")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000, type=int)
@click.pass_obj
def web(obj: dict, host: str, port: int) -> None:
    """Run web interface."""
    from ally.web.app import create_app

    app = create_app(obj["path"])
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
