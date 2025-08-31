import argparse
import json

from .service import (
    export_entries,
    init_storage,
    list_entries,
    list_threads,
    pulse,
    write_entry,
)


def main():
    parser = argparse.ArgumentParser(prog="ally")
    parser.add_argument("--path", default="data")
    parser.add_argument("--log", default="audit.jsonl")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init")

    w = sub.add_parser("write")
    w.add_argument("text")
    w.add_argument("--style", default="gentle")

    l = sub.add_parser("list")
    l.add_argument("--limit", type=int, default=10)

    sub.add_parser("threads")
    sub.add_parser("pulse")

    ex = sub.add_parser("export")
    ex.add_argument("--fmt", choices=["md", "json"], default="md")
    ex.add_argument("--out", default="export.md")

    args = parser.parse_args()

    if args.cmd == "init":
        init_storage("files", args.path, args.log)
        print("storage initialized")
    elif args.cmd == "write":
        resp = write_entry("files", args.path, args.log, args.text, args.style)
        print(resp)
    elif args.cmd == "list":
        entries = list_entries("files", args.path, args.limit)
        for e in entries:
            thread = e["threads"][0] if e["threads"] else ""
            preview = e["text"][:120].replace("\n", " ")
            print(f"{e['timestamp']} | {thread} | {preview}")
    elif args.cmd == "threads":
        th = list_threads("files", args.path)
        for t, c in th.items():
            print(f"{t}: {c}")
    elif args.cmd == "pulse":
        data = pulse("files", args.path)
        print(json.dumps(data, ensure_ascii=False))
    elif args.cmd == "export":
        export_entries("files", args.path, args.fmt, args.out, args.log)
        print(f"exported to {args.out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
