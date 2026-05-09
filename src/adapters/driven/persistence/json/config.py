from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var


@dataclass(frozen=True)
class JSONConfig:
    """JSON persistence configuration.

    Args:
        state_path: Default JSON world-state import/export path.
        export_dir: Default JSON export directory.
        user_store_path: JSON user-store path.
    """

    state_path: Path
    export_dir: Path
    user_store_path: Path


_json_config: JSONConfig | None = None


def load_json_config() -> JSONConfig:
    """Load JSON persistence configuration from environment variables."""
    load_dotenv()

    return JSONConfig(
        state_path=Path(get_env_var("JSON_STATE_PATH", "state.json")),
        export_dir=Path(get_env_var("JSON_EXPORT_DIR", "exports")),
        user_store_path=Path(get_env_var("JSON_USER_STORE_PATH", "users.json")),
    )


def get_json_config() -> JSONConfig:
    """Return cached JSON config, loading it lazily on first use."""
    global _json_config

    if _json_config is None:
        _json_config = load_json_config()

    return _json_config


def set_json_config(config: JSONConfig | None) -> None:
    """Override or clear JSON config, mainly for tests."""
    global _json_config

    _json_config = config
