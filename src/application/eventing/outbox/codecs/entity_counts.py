"""Flat world-state count fields shared by versioned outbox payload codecs.

These helpers preserve the outbox wire format, which differs from the nested
plural-key objects used by audit projections. The owning codec remains
responsible for validating the complete payload's required and unexpected keys.
"""

from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject
from src.shared.validation import require_non_negative_int


def encode_entity_counts(counts: WorldStateEntityCounts, *, prefix: str = "") -> JSONObject:
    """Project a validated count snapshot into four flat JSON integer fields.

    Args:
        counts: Validated customer, package, route, and truck count snapshot.
        prefix: Literal prefix added to each wire key, including any separator.
            Existing codecs use ``""``, ``"previous_"``, or ``"new_"``.

    Returns:
        A fresh object with customer_count, package_count, route_count, and
        truck_count keys, each prefixed as requested. Values are not coerced.

    This is a projection, not an additional validation boundary. Current codec
    adapters enforce replay validity before payloads are used for durable writes.
    """
    return {
        f"{prefix}customer_count": counts.customers,
        f"{prefix}package_count": counts.packages,
        f"{prefix}route_count": counts.routes,
        f"{prefix}truck_count": counts.trucks,
    }


def decode_entity_counts(payload: JSONObject, *, prefix: str = "") -> WorldStateEntityCounts:
    """Validate and reconstruct one flat count snapshot from a codec payload.

    Args:
        payload: Event payload whose complete key set was checked by its codec.
            Only the selected four count fields are read; other fields are ignored.
        prefix: Literal prefix identifying the count group, using the same
            convention as :func:`encode_entity_counts`.

    Returns:
        A new validated count snapshot independent of the input object. Zero
        and arbitrarily large non-negative integers are preserved without coercion.

    Raises:
        KeyError: If a selected count key is missing. The owning codec normally
            reports missing keys before calling this helper.
        TypeError: If a selected count is not an integer, including booleans.
        ValueError: If a selected count is negative.

    Validation uses the full wire key in errors, preserving which before/after
    field failed. The payload is not mutated or retained.
    """
    return WorldStateEntityCounts(
        customers=require_non_negative_int(payload[f"{prefix}customer_count"], f"{prefix}customer_count"),
        packages=require_non_negative_int(payload[f"{prefix}package_count"], f"{prefix}package_count"),
        routes=require_non_negative_int(payload[f"{prefix}route_count"], f"{prefix}route_count"),
        trucks=require_non_negative_int(payload[f"{prefix}truck_count"], f"{prefix}truck_count"),
    )
