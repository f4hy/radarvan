"""Webhook reporting for authorization decisions.

Its own module because it belongs to neither of its neighbours: dependencies.py
holds DI singletons and the gates themselves, notify.py owns webhook transport
and throttling, and this is the small piece in between that turns a rejected
request into a message. Both the gates and main.py's HTTPException handler
import it, so putting it in dependencies.py would mean app composition reaching
into the DI module for an exception-handler helper - and would drag
middleware.py into every router's import graph.
"""

from fastapi import Request

from .middleware import client_key
from .notify import notify_throttled

API_KEY_HEADER = "X-API-Key"


def _session_user_id(request: Request) -> int | None:
    """The logged-in user id from the signed cookie, if any.

    Read straight off the scope rather than through ``get_current_user``: this
    runs on the rejection path, where a DB lookup just to decorate a message is
    not worth a second failure mode. ``request.session`` is avoided because it
    asserts SessionMiddleware is installed, and asserts vanish under ``-O``.
    """
    session = request.scope.get("session") or {}
    user_id: int | None = session.get("user_id")
    return user_id


def notify_auth_event(request: Request, status: int | None, detail: str) -> None:
    """Report an auth decision to the notify webhook, throttled per client+route.

    ``status`` is the rejection status, or None for the "would have been
    rejected" case that an unset ENFORCE_AUTH lets through - the latter is the
    whole point of observe-only mode, so it is worth the same visibility.
    Formatting the outcome here (rather than taking a pre-built string) keeps
    it out of the throttle key, where a caller wording it differently would
    silently earn its own bucket.
    """
    outcome = f"rejected {status}" if status is not None else "allowed"
    client = client_key(request)
    method, path = request.method, request.scope["path"]
    notify_throttled(
        f"{client}|{method}|{path}|{outcome}",
        f"Auth {outcome}: {method} {path} from {client} "
        f"(key_present={API_KEY_HEADER in request.headers}, "
        f"user_id={_session_user_id(request)}) - {detail}",
    )
