import os
import sys
from pathlib import Path
import time 


# Calculate the path to the directory above "migrations"
root_dir = Path(__file__).resolve().parent.parent

# Add this directory to sys.path
sys.path.append(str(root_dir))
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from urllib.parse import urlparse

from alembic import context
from dotenv import load_dotenv

from app.models.base_models.base import Base
from app.models.maindb import *
from app.models.admindb import *


load_dotenv()
config = context.config

db_name = (
    config.config_ini_section
)
    
  # active config ini section is the db name that we have chosen
db_dsn = os.environ[f"DATOX_DATABASE__{db_name.upper()}_DSN"]
print(db_dsn)
config.set_main_option(
    "sqlalchemy.url", db_dsn
)

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
    print(url, " rererere")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=db_name,
        version_locations=config.get_main_option("version_locations")
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print(" rererere")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    def include_object(object, name, type_, reflected, compare_to):
        if (
            type_ == "foreign_key_constraint"
            and compare_to
            and (
                compare_to.elements[0].target_fullname
                == db_name + "." + object.elements[0].target_fullname
                or db_name + "." + compare_to.elements[0].target_fullname
                == object.elements[0].target_fullname
            )
        ):
            return False
        if type_ == "table":
            db = object.info.get("dbname")
            if db == db_name or db is None:
                return True
        elif (
            object.table.info.get("dbname") == db_name
            or object.table.info.get("dbname") is None
        ):
            return True
        else:
            return False

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
