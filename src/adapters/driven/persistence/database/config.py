"""PostgreSQL configuration loaded from environment variables."""

from dataclasses import dataclass

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var


@dataclass(frozen=True)
class PostgresConfig:
    """Connection settings for the PostgreSQL adapter.

    Args:
        host: Database host address.
        name: Database name.
        user: Database username.
        password: Database password.
        port: Database port number (default: 5432).
    """

    host: str
    name: str
    user: str
    password: str
    port: int = 5432


_db_config: PostgresConfig | None = None


def load_postgres_config() -> PostgresConfig:
    """Load PostgreSQL configuration from environment variables."""
    load_dotenv()

    return PostgresConfig(
        host=get_env_var("DB_HOST", "localhost"),
        name=get_env_var("DB_NAME"),
        user=get_env_var("DB_USER"),
        password=get_env_var("DB_PASSWORD"),
        port=_read_port(),
    )


def get_postgres_config() -> PostgresConfig:
    """Return cached PostgreSQL config, loading it lazily on first use."""
    global _db_config

    if _db_config is None:
        _db_config = load_postgres_config()

    return _db_config


def set_postgres_config(config: PostgresConfig | None) -> None:
    """Override or clear PostgreSQL config, mainly for tests."""
    global _db_config

    _db_config = config


def _read_port() -> int:
    raw_port = get_env_var("DB_PORT", "5432")

    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f"DB_PORT must be an integer, got {raw_port!r}.") from exc

    if port <= 0:
        raise ValueError(f"DB_PORT must be positive, got {port}.")

    return port
