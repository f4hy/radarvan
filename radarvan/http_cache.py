"""Cache headers for the built frontend.

Starlette's StaticFiles sends an ETag and a Last-Modified but no Cache-Control
at all, which leaves the decision to the browser's *heuristic* freshness -
roughly a tenth of the file's age, reused without asking. Two rules fix that,
and they are the standard ones for a Vite/SPA build:

* ``/assets/*`` is content-hashed, so a changed bundle is a changed URL and the
  old one is never requested again. Immutable, cached for a year.
* everything else - ``index.html`` above all - revalidates. A stale index is the
  whole app going stale, because it names the previous build's bundles and no
  amount of correct API headers can undo that.

The ``/assets/`` test is against the request path, so this assumes the mount is
at the site root; under a prefix the hashed bundles would quietly fall back to
revalidating on every load.
"""

import os

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

_IMMUTABLE = "public, max-age=31536000, immutable"


class CachedStaticFiles(StaticFiles):
    """StaticFiles that says how long each kind of file may be kept."""

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        is_asset = scope["path"].startswith("/assets/")
        response.headers["Cache-Control"] = _IMMUTABLE if is_asset else "no-cache"
        return response
