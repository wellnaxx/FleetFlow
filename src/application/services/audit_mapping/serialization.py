"""Audit-specific JSON serialization helpers."""

from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject


def entity_counts_payload(entity_counts: WorldStateEntityCounts) -> JSONObject:
    """Serialize validated world-state entity counts as a JSON object."""
    return {
        "customers": entity_counts.customers,
        "packages": entity_counts.packages,
        "routes": entity_counts.routes,
        "trucks": entity_counts.trucks,
    }
