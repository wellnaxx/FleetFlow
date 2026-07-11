"""Tests for heartbeat reconciliation result models."""

import unittest
from typing import cast

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.results.truck_reconciliation_summary_result import (
    TruckReconciliationSummary,
)
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


class _EqualRecorder:
    """Recorder stub whose instances deliberately compare equal."""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _EqualRecorder)

    def __hash__(self) -> int:
        return 1


class HeartbeatSummaryShould(unittest.TestCase):
    """Validate heartbeat summary aggregation behavior."""

    def test_event_recorders_deduplicate_by_identity_and_preserve_order(self) -> None:
        first_package = cast(DeliveryPackage, _EqualRecorder())
        second_package = cast(DeliveryPackage, _EqualRecorder())
        route = cast(DeliveryRoute, _EqualRecorder())
        summary = HeartbeatSummary(
            mutated_routes=(route, route),
            mutated_packages=(first_package, first_package, second_package),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
        )

        recorders = summary.event_recorders

        self.assertEqual(len(recorders), 3)
        self.assertIs(recorders[0], route)
        self.assertIs(recorders[1], first_package)
        self.assertIs(recorders[2], second_package)

    def test_reconciled_truck_counts_as_changed_state(self) -> None:
        truck = cast(Truck, object())
        summary = HeartbeatSummary(
            mutated_routes=(),
            mutated_packages=(),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
            mutated_trucks_reconciled=(truck,),
        )

        self.assertEqual(summary.trucks_reconciled, 1)
        self.assertTrue(summary.state_changed)

    def test_truck_summary_counts_reference_repair_as_changed_state(self) -> None:
        truck = cast(Truck, object())

        self.assertTrue(TruckReconciliationSummary(trucks_reconciled=(truck,)).state_changed)


if __name__ == "__main__":
    unittest.main()
