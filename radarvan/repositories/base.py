"""Common base class for per-entity repositories.

A repo is a thin wrapper around a SQLAlchemy `Session` that exposes
operations on a single entity (or a tightly coupled cluster of entities).

Repos share:
- `auto_commit`: when True (default), each mutating method commits on its own.
  Callers can flip to False to batch many writes into one transaction; do not
  forget to call `session.commit()` yourself in that mode.
- `notify`: when True, write methods call out to the side-channel notifier
  (currently Slack). Default False so background backfills stay silent.
"""

from sqlalchemy.orm import Session


class BaseRepo:
    def __init__(
        self,
        session: Session,
        notify: bool = False,
        auto_commit: bool = True,
    ):
        self.session = session
        self.notify = notify
        self.auto_commit = auto_commit

    def _commit_if_auto(self) -> None:
        if self.auto_commit:
            self.session.commit()
