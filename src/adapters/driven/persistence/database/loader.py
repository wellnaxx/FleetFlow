"""Load SQL query files for the database adapter."""

from functools import cache
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"


@cache
def load_sql(relative_path: str) -> str:
    """Load a SQL file from the database/sql directory.

    Args:
        relative_path: Path relative to the sql directory, e.g.
            "customers/select_by_id.sql".

    Returns:
        SQL text.

    Raises:
        FileNotFoundError: If the query file does not exist.
    """
    path = SQL_DIR / relative_path

    if not path.is_file():
        raise FileNotFoundError(f"SQL query file not foundL {path}")
    return path.read_text(encoding="utf8").strip()
