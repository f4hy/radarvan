"""Deploy-time configuration: the `Procfile` release phase and what it needs.

`release: alembic upgrade head` runs unattended on every Heroku deploy, and a
failing release phase blocks the deploy. The invariants it rests on are all
invisible from application code — nothing imports them, no other test touches
them, and each one broke the phase when it was first set up. They are pinned
here so a plausible-looking cleanup fails in CI rather than on a push to
production.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def _procfile() -> dict[str, str]:
    entries = {}
    for line in (ROOT / "Procfile").read_text().splitlines():
        if ":" in line:
            name, _, command = line.partition(":")
            entries[name.strip()] = command.strip()
    return entries


def test_the_release_phase_applies_migrations() -> None:
    assert _procfile().get("release") == "alembic upgrade head"


def test_the_web_process_survives_alongside_it() -> None:
    """A Procfile is rewritten wholesale; losing `web` takes the app down."""
    assert _procfile().get("web") == "fastapi run radarvan/main.py"


def test_alembic_is_a_runtime_dependency_not_a_dev_one() -> None:
    """Heroku's buildpack installs `uv sync --no-dev`.

    In the dev group, alembic is simply absent from the slug and the release
    phase dies with "alembic: not found" - taking the deploy with it.
    """
    project = _pyproject()
    runtime = " ".join(project["project"]["dependencies"])
    dev = " ".join(project.get("dependency-groups", {}).get("dev", []))
    assert "alembic" in runtime
    assert "alembic" not in dev


def test_alembic_env_normalizes_the_legacy_postgres_scheme() -> None:
    """Heroku's addon-managed DATABASE_URL uses `postgres://`.

    SQLAlchemy 2.x has no dialect under that name. Normalizing in
    `bootstrap_db.py` does not help here: `alembic upgrade` re-reads the raw
    environment variable in its own process.
    """
    env = (ROOT / "alembic" / "env.py").read_text()
    assert 'os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")' in env


def test_alembic_env_does_not_log_the_password() -> None:
    """Release-phase output is app log, readable by anyone with access."""
    env = (ROOT / "alembic" / "env.py").read_text()
    assert "print(\"using db url\", _redacted(db_url))" in env
    assert "print(\"using db url\", db_url)" not in env
