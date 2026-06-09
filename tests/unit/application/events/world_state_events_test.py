"""Tests for world-state event value objects and failure classifications."""

from datetime import datetime

import pytest

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateImportFailed,
)
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts


def test_world_state_entity_counts_accept_non_negative_integers() -> None:
    counts = WorldStateEntityCounts(
        customers=0,
        packages=3,
        routes=2,
        trucks=1,
    )

    assert counts.customers == 0
    assert counts.packages == 3
    assert counts.routes == 2
    assert counts.trucks == 1


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("customers", -1),
        ("packages", -1),
        ("routes", -1),
        ("trucks", -1),
        ("customers", True),
        ("packages", 1.5),
        ("routes", "1"),
        ("trucks", None),
    ],
)
def test_world_state_entity_counts_reject_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    values: dict[str, object] = {
        "customers": 0,
        "packages": 0,
        "routes": 0,
        "trucks": 0,
    }
    values[field_name] = invalid_value

    with pytest.raises(ValueError, match=rf"^{field_name} must be a non-negative integer\.$"):
        WorldStateEntityCounts(**values)  # type: ignore[arg-type]


def test_unsupported_schema_failure_and_corruption_reasons_remain_distinct_types() -> None:
    occurred_at = datetime(2026, 6, 9, 12, 0)

    failed = WorldStateImportFailed(
        snapshot_path="state.json",
        schema_version=3,
        reason=WorldStateFailureReason.UNSUPPORTED_SCHEMA,
        occurred_at=occurred_at,
    )
    corruption = WorldStateCorruptionDetected(
        snapshot_path="state.json",
        reason=WorldStateCorruptionReason.UNSUPPORTED_SCHEMA,
        occurred_at=occurred_at,
    )

    assert failed.reason is WorldStateFailureReason.UNSUPPORTED_SCHEMA
    assert corruption.reason is WorldStateCorruptionReason.UNSUPPORTED_SCHEMA
