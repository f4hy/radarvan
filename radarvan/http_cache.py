"""Serving the built frontend: cache headers, and the SPA fallback.

Cache headers. Starlette's StaticFiles sends an ETag and a Last-Modified but no
Cache-Control at all, which leaves the decision to the browser's *heuristic*
freshness - roughly a tenth of the file's age, reused without asking. Two rules
fix that, and they are the standard ones for a Vite/SPA build:

* ``/assets/*`` is content-hashed, so a changed bundle is a changed URL and the
  old one is never requested again. Immutable, cached for a year.
* everything else - ``index.html`` above all - revalidates. A stale index is the
  whole app going stale, because it names the previous build's bundles and no
  amount of correct API headers can undo that.

The ``/assets/`` test is against the request path, so this assumes the mount is
at the site root; under a prefix the hashed bundles would quietly fall back to
revalidating on every load.

SPA fallback. The frontend routes on the path (``/game-night``, not
``/?page=game-night``), and nothing on disk matches those paths - so a hard
refresh, a bookmark, or a link pasted into Discord would 404 without this.
``html=True`` alone does not cover it: it serves ``index.html`` for ``/`` and
looks for a ``404.html``, but never falls back for an arbitrary path.

What must *not* fall back is the API. This mount sits at ``/`` and is registered
last, so every request that matched no API route arrives here - including a
typo'd or removed ``/api/...`` path. Those have to keep their JSON 404, both
because a client parsing HTML as JSON fails confusingly and because
``main.handle_http_exception`` reports 401/403 from that same path space. Hence
the explicit ``/api`` exclusion rather than a blanket fallback.
"""

import os
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

_IMMUTABLE = "public, max-age=31536000, immutable"

# Paths the fallback must never claim: they belong to the API, and a 404 there
# is an answer, not a missing page.
_API_PREFIX = "api"


class CachedStaticFiles(StaticFiles):
    """StaticFiles that says how long each kind of file may be kept, and serves
    ``index.html`` for client-routed paths."""

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

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or not self._is_client_route(path):
                raise
            # Serve the app shell and let the router decide what the path
            # means. 200, not 404: this *is* a real page as far as the client
            # is concerned, and a 404 status would keep it out of history and
            # confuse anything reading the status (link unfurlers included).
            return await super().get_response("index.html", scope)

    @staticmethod
    def _is_client_route(path: str) -> bool:
        """True for a path the React router should get a chance to handle.

        ``path`` is relative to the mount point (no leading slash), which is the
        site root here. A missing file under ``/assets/`` is a genuine 404 - the
        bundle names are content-hashed, so a miss there means a stale
        ``index.html`` is naming a build that no longer exists, and quietly
        handing back HTML would turn that into a syntax error in the console
        instead of a 404 in the network tab.
        """
        first = Path(path).parts[0] if path else ""
        return first not in (_API_PREFIX, "assets")
