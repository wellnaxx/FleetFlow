"""Shared JSON serialization helpers for audit descriptor mappings."""

from datetime import datetime

from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject


def optional_id(value: object | None) -> str | None:
    """Serialize an optional identifier without converting ``None`` to text."""
    return str(value) if value is not None else None


def optional_str(value: object | None) -> str | None:
    """Serialize an optional value without converting ``None`` to text."""
    return str(value) if value is not None else None


def optional_isoformat(value: datetime | None) -> str | None:
    """Serialize an optional datetime in ISO 8601 format."""
    return value.isoformat() if value is not None else None


def entity_counts_payload(entity_counts: WorldStateEntityCounts) -> JSONObject:
    """Serialize validated world-state entity counts as a JSON object."""
    return {
        "customers": entity_counts.customers,
        "packages": entity_counts.packages,
        "routes": entity_counts.routes,
        "trucks": entity_counts.trucks,
    }
