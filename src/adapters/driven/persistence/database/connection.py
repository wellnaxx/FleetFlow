import psycopg
from psycopg import Connection

from src.adapters.driven.persistence.database.config import get_postgres_config


def get_connection() -> Connection:
    config = get_postgres_config()

    return psycopg.connect(
        dbname=config.name,
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
    )
