"""Shared pytest bootstrap.

radarvan.dependencies reads DATABASE_URL at import time (and fails fast when
it's missing - desirable in production). Tests never open a real connection
(create_engine doesn't connect), so inject a placeholder before any test
module imports the app. setdefault keeps a real value (e.g. the dev shell's)
untouched.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/radarvan_test")
