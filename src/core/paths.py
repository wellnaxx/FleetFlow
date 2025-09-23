import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

def ensure_data_dir() -> None:
    """Create the data/ directory if missing."""
    os.makedirs(DATA_DIR, exist_ok=True)

def resolve_data_path(name_or_path: str | None) -> str:
    """Resolve a filename or path to an absolute path, defaulting to data/.

    - Bare filenames like "state.json" become "<project>/data/state.json".
    - Paths with separators (e.g., "backups/foo.json" or "/abs/path.json")
      are normalized relative to project root and returned absolute.
    """
    ensure_data_dir()
    if not name_or_path:
        return os.path.join(DATA_DIR, "state.json")
    if os.path.sep in name_or_path or name_or_path.startswith("."):
        return os.path.abspath(os.path.join(PROJECT_ROOT, name_or_path))
    return os.path.join(DATA_DIR, name_or_path)