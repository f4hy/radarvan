from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
from radarvan.db import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Heroku's addon-managed DATABASE_URL uses the legacy ``postgres://`` scheme,
# which SQLAlchemy 2.x refuses to load a dialect for. `db_utils` and
# `scripts/bootstrap_db.py` both normalize it; this file has to do it too
# rather than rely on them, because `alembic upgrade` re-reads the raw
# environment variable in its own process - normalizing before shelling out to
# alembic does nothing for the subprocess.
db_url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://")


def _redacted(url: str) -> str:
    """The URL with its password masked.

    This line lands in the Heroku release-phase log on every deploy, which is
    readable by anyone with access to the app - a full DSN there is a leaked
    database credential.
    """
    scheme, _, rest = url.partition("://")
    if "@" not in rest:
        return url
    creds, _, host = rest.partition("@")
    user, _, password = creds.partition(":")
    return f"{scheme}://{user}{':***' if password else ''}@{host}"


print("using db url", _redacted(db_url))
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
