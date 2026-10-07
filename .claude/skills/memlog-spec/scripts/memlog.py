#!/usr/bin/env python3
"""memlog — an append-only memory log for a skill (short version of BMad's memlog.py).

Three rules:
  1. Append-only, chronological. No edit or delete command: a later entry supersedes an earlier one.
  2. Blind writes. Every command echoes the new state as one line of JSON, so the caller never
     re-reads the file mid-session. The caller reads the file itself, only when resuming.
  3. No status field. "Done" or "blocked" is recorded as an entry: append --type event --text "...".

File shape (.memlog.md):

    ---
    topic: Expense report export
    updated: 2026-10-07T14:22
    ---

    - (capability) CAP-1 export the month as CSV; success: the file opens in Excel with one row per expense
    - (decision by user) CAP-1 also exports PDF

Commands:
  init   (--workspace DIR | --path FILE) [--field k=v ...]           create the memlog (error if it exists)
  append (--workspace DIR | --path FILE) --text STR [--type T] [--by W]  add one entry at the end
  set    (--workspace DIR | --path FILE) --key K --value V           set a frontmatter field
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

MEMLOG = ".memlog.md"


def resolve(args) -> Path:
    return Path(args.path) if args.path else Path(args.workspace) / MEMLOG


def split(text: str):
    """(frontmatter dict, body). The fence closes on the first line that is exactly '---'."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(".memlog.md has no frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if end is None:
        raise ValueError(".memlog.md frontmatter is not terminated")
    meta = {}
    for line in lines[1:end]:
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, "\n".join(lines[end + 1 :]).lstrip("\n")


def render(meta: dict, body: str) -> str:
    fm = "\n".join(f"{k}: {' '.join(str(v).splitlines())}" for k, v in meta.items())
    return "---\n" + fm + "\n---\n\n" + body.rstrip("\n") + "\n"


def touch(meta: dict) -> None:
    """Stamp `updated` and keep it last."""
    meta.pop("updated", None)
    meta["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M")


def write_atomic(path: Path, text: str) -> None:
    """Temp file + fsync + rename: a crash leaves the old file or the new one, never half of one."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def ack(path: Path, body: str) -> None:
    entries = sum(1 for ln in body.splitlines() if ln.startswith("- "))
    print(json.dumps({"ok": True, "memlog": str(path), "entries": entries}, ensure_ascii=False))


def cmd_init(args) -> int:
    path = resolve(args)
    if path.exists():
        print(f"error: {path} already exists; use append or set", file=sys.stderr)
        return 2
    meta = {}
    for pair in args.field or []:
        if "=" not in pair:
            print(f"error: --field expects key=value, got {pair!r}", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        meta[k.strip()] = v.strip()
    touch(meta)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, render(meta, ""))
    ack(path, "")
    return 0


def cmd_append(args) -> int:
    path = resolve(args)
    raw = path.read_text(encoding="utf-8")
    split(raw)  # a missing or malformed log fails here, before anything is written
    text = " ".join(args.text.split())  # one entry = one line
    label = args.type or ""
    if args.by:
        label = f"{label} by {args.by}".strip()
    entry = f"- ({label}) {text}" if label else f"- {text}"
    # Enough for one writer. BMad's memlog.py opens a FILE_APPEND_DATA handle on Windows so that
    # parallel subagents appending at the same moment never overwrite each other.
    with open(path, "a", encoding="utf-8") as f:
        f.write(("" if raw.endswith("\n") else "\n") + entry + "\n")
        f.flush()
        os.fsync(f.fileno())
    ack(path, split(path.read_text(encoding="utf-8"))[1])
    return 0


def cmd_set(args) -> int:
    path = resolve(args)
    meta, body = split(path.read_text(encoding="utf-8"))
    meta[args.key] = args.value
    touch(meta)
    write_atomic(path, render(meta, body))
    ack(path, body)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def target(sp):
        g = sp.add_mutually_exclusive_group(required=True)
        g.add_argument("--workspace", help="run folder; the memlog is {workspace}/.memlog.md")
        g.add_argument("--path", help="explicit memlog file path")

    pi = sub.add_parser("init", help="create the memlog")
    target(pi)
    pi.add_argument("--field", action="append", metavar="KEY=VALUE", help="frontmatter field (repeatable)")
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append", help="add one entry at the end")
    target(pa)
    pa.add_argument("--text", required=True)
    pa.add_argument("--type", help="entry kind, rendered as (type)")
    pa.add_argument("--by", help="who it came from, rendered as (type by who)")
    pa.set_defaults(func=cmd_append)

    ps = sub.add_parser("set", help="set a frontmatter field")
    target(ps)
    ps.add_argument("--key", required=True)
    ps.add_argument("--value", required=True)
    ps.set_defaults(func=cmd_set)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
