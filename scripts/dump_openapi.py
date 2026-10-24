"""Write the app's OpenAPI spec to a file without running the server.

    uv run python scripts/dump_openapi.py <out.json>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# DEV exposes the include_in_schema=IS_DEV routes the committed client is built
# with; the database URL is never connected to while building the spec.
os.environ.setdefault("DEV", "1")
os.environ.setdefault("DATABASE_URL", "sqlite://")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radarvan.main import app

Path(sys.argv[1]).write_text(json.dumps(app.openapi(), indent=2) + "\n")
