from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# Add project root directory to path to allow importing models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

def get_db_url():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/leadhunter_db")
    if "YOUR_POSTGRES_PASSWORD" in db_url:
        db_url = db_url.replace("YOUR_POSTGRES_PASSWORD", "postgres")
    return db_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_db_url()
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
