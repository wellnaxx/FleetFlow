"""Tests for world-state event value objects and failure classifications."""

import unittest
from datetime import datetime

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateImportFailed,
)
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts


class WorldStateEventShould(unittest.TestCase):
    def test_entity_counts_accept_non_negative_integers(self) -> None:
        counts = WorldStateEntityCounts(
            customers=0,
            packages=3,
            routes=2,
            trucks=1,
        )

        self.assertEqual(counts.customers, 0)
        self.assertEqual(counts.packages, 3)
        self.assertEqual(counts.routes, 2)
        self.assertEqual(counts.trucks, 1)

    def test_entity_counts_reject_invalid_values(self) -> None:
        invalid_values: tuple[tuple[str, object], ...] = (
            ("customers", -1),
            ("packages", -1),
            ("routes", -1),
            ("trucks", -1),
            ("customers", True),
            ("packages", 1.5),
            ("routes", "1"),
            ("trucks", None),
        )

        for field_name, invalid_value in invalid_values:
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                values: dict[str, object] = {
                    "customers": 0,
                    "packages": 0,
                    "routes": 0,
                    "trucks": 0,
                }
                values[field_name] = invalid_value

                with self.assertRaisesRegex(
                    ValueError,
                    rf"^{field_name} must be a non-negative integer\.$",
                ):
                    WorldStateEntityCounts(**values)  # type: ignore[arg-type]

    def test_unsupported_schema_failure_and_corruption_reasons_remain_distinct_types(self) -> None:
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

        self.assertIs(failed.reason, WorldStateFailureReason.UNSUPPORTED_SCHEMA)
        self.assertIs(corruption.reason, WorldStateCorruptionReason.UNSUPPORTED_SCHEMA)
