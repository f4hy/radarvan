#!/usr/bin/env python
"""Development-only DB schema diagram, via eralchemy2.

Renders the schema as an ER diagram. Dev tooling: nothing in the app imports
this and it ships no route.

    make schema        # build/db_schema.svg + build/db_schema.md (mermaid)
    make schema-open   # ... and open the SVG
    make schema-live   # read the real database instead of the ORM models

By default it reads the ORM models in ``radarvan/db.py``, so no database
connection is needed. ``--live`` renders whatever is actually in
``$DATABASE_URL`` instead, which is how you spot drift from the models.

Output format follows the file extension - eralchemy2 handles .svg, .png, .pdf,
.dot, .er and .md (mermaid, paste-able into GitHub).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import webbrowser

from eralchemy2 import render_er

# The repo root holds the `radarvan` package but isn't on sys.path for a script
# living in tools/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radarvan.db import Base

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_database_url() -> str | None:
    """$DATABASE_URL, falling back to the repo's .env (no dotenv dependency)."""
    import os

    from_env = os.getenv("DATABASE_URL")
    if from_env:
        return from_env.replace("postgres://", "postgresql://")
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "DATABASE_URL":
            url = value.strip().strip("\"'")
            return url.replace("postgres://", "postgresql://") or None
    return None


def render(source: object, out: Path) -> None:
    """eralchemy2 ships no type hints; keep the untyped call in one place."""
    render_er(source, str(out))  # type: ignore[no-untyped-call]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("build/db_schema.svg"),
        help="output path; the extension picks the format (default: build/db_schema.svg)",
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="also write a mermaid .md next to the diagram",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="render the real database at $DATABASE_URL instead of the ORM models",
    )
    parser.add_argument(
        "--open", dest="open_it", action="store_true", help="open when done"
    )
    args = parser.parse_args(argv)

    source: object = Base
    if args.live:
        url = resolve_database_url()
        if not url:
            parser.error("--live needs DATABASE_URL (env or .env) to be set")
        source = url

    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    render(source, out)
    written = [out]
    if args.mermaid:
        mermaid = out.with_suffix(".md")
        render(source, mermaid)
        written.append(mermaid)

    for path in written:
        sys.stdout.write(f"{path.resolve()}\n")
    if args.open_it:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
