from __future__ import annotations

import argparse
import json
import sys

from .ledger import Ledger


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="hardtack",
        description="Local-first, append-only context ledger for sovereign human-AI collaboration.",
    )
    parser.add_argument("--dir", default=".hardtack", help="Ledger directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize a new ledger")

    p_log = sub.add_parser("log", help="Append an entry")
    p_log.add_argument("--role", required=True, help="Role (human, machine, system)")
    p_log.add_argument("--content", required=True, help="Entry content")
    p_log.add_argument("--meta", help="Optional JSON metadata")

    sub.add_parser("verify", help="Verify hash chain integrity")

    p_search = sub.add_parser("search", help="Search entries")
    p_search.add_argument("query", help="Search query")

    p_export = sub.add_parser("export", help="Export Markdown")
    p_export.add_argument("--output", help="Output file (default stdout)")

    args = parser.parse_args(argv)
    ledger = Ledger(args.dir)

    if args.command == "init":
        print(f"Initialized ledger at {ledger.root}")
    elif args.command == "log":
        meta = json.loads(args.meta) if args.meta else None
        entry = ledger.log(args.role, args.content, meta)
        print(entry["hash"])
    elif args.command == "verify":
        ok = ledger.verify()
        print("VALID" if ok else "INVALID")
        sys.exit(0 if ok else 1)
    elif args.command == "search":
        for e in ledger.search(args.query):
            print(f"[{e['timestamp']}] {e['role']}: {e['content']}")
    elif args.command == "export":
        md = ledger.export_markdown()
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Exported to {args.output}")
        else:
            print(md)


if __name__ == "__main__":
    main()
