"""Default state persistence configuration."""

from src.adapters.driven.persistence.json.paths import resolve_data_path

DEFAULT_WORLD_STATE_PATH = resolve_data_path("state.json")
