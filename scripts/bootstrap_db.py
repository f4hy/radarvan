"""Bring the database pointed at by DATABASE_URL to the alembic head.

Run by the compose `migrate` service on every `docker compose up`.

Why this exists instead of a plain `alembic upgrade head`: the migration chain
cannot build the schema from nothing. `4efb2f28e765_initial_migration` is an
empty `pass` -- alembic was introduced against an already-populated production
database and stamped on top of it -- so every later revision ALTERs tables no
revision ever created. Running the chain against an empty database fails on the
first one (`DROP TABLE generals`).

So there are two cases:

* Database has an `alembic_version` table (a restored production snapshot, or a
  local database this script already set up): run the migrations normally. This
  is the path that matters -- it is how you test a new migration locally against
  real data before it ever touches production.
* Database is empty: create the schema straight from the ORM models
  (`Base.metadata.create_all`) and `alembic stamp head`, so subsequent
  migrations apply cleanly.
"""

from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect


def main() -> int:
    url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())

    if "alembic_version" in tables:
        print(f"==> {len(tables)} tables, alembic_version present: upgrade head")
        return subprocess.call(["alembic", "upgrade", "head"])

    if tables:
        print(
            "==> database has tables but no alembic_version; refusing to guess.\n"
            "    Either restore a snapshot (./scripts/db_restore.sh) or wipe it\n"
            "    (make db-reset).",
            file=sys.stderr,
        )
        return 1

    print("==> empty database: creating schema from the ORM models")
    from radarvan.db import Base

    Base.metadata.create_all(engine)
    print("==> stamping alembic head")
    return subprocess.call(["alembic", "stamp", "head"])


if __name__ == "__main__":
    raise SystemExit(main())
