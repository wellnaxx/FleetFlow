import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from src.adapters.driven.persistence.json.config import get_json_config
from src.adapters.driven.persistence.json.paths import resolve_data_path

_SNAPSHOT_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


class WorldStatePathRequest(BaseModel):
    """Request model for saving or loading a world-state snapshot path."""

    path: str = Field(
        ...,
        max_length=255,
        description="Snapshot file path to save to or load from.",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        """Resolve a safe snapshot path under the configured export directory."""
        candidate_text = value.strip()
        if not candidate_text:
            raise ValueError("Snapshot path is required.")
        if not _SNAPSHOT_PATH_PATTERN.fullmatch(candidate_text):
            raise ValueError("Snapshot path contains unsupported characters.")

        candidate = Path(candidate_text)
        if candidate.is_absolute():
            raise ValueError("Snapshot path must be relative.")
        if ".." in candidate.parts:
            raise ValueError("Snapshot path cannot contain traversal segments.")

        base_dir = Path(resolve_data_path(str(get_json_config().export_dir))).resolve()
        resolved = (base_dir / candidate).resolve()

        try:
            resolved.relative_to(base_dir)
        except ValueError as exc:
            raise ValueError("Snapshot path must stay within the export directory.") from exc

        return str(resolved)


class WorldStatePathResponse(BaseModel):
    """Response model for a resolved world-state snapshot path."""

    path: str = Field(..., description="Resolved snapshot file path used by the state operation.")
    message: str = Field(..., description="Message describing the result of the endpoint")
