"""Tests for schedule-derived reconciliation event contracts."""

import unittest
from datetime import datetime

from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.events.reconciliation_events import (
    PackageStateReconciled,
    RouteStateReconciled,
)
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode


class ReconciliationEventShould(unittest.TestCase):
    """Validate reconciliation reason and schedule-evidence contracts."""

    def test_accept_multiple_unique_package_reasons(self) -> None:
        event = PackageStateReconciled(
            package_id=7,
            route_id=3,
            previous_status=ItemStatus.TODO,
            new_status=ItemStatus.IN_PROGRESS,
            previous_location=LocationCode("SYD"),
            new_location=LocationCode("MEL"),
            previous_expected_arrival=None,
            new_expected_arrival=datetime(2026, 7, 10, 14, 0),
            scheduled_pickup_time=datetime(2026, 7, 10, 10, 0),
            scheduled_delivery_time=datetime(2026, 7, 10, 14, 0),
            reasons=(
                PackageReconciliationReason.ROUTE_PROGRESS_ADVANCED,
                PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED,
            ),
            occurred_at=datetime(2026, 7, 10, 12, 0),
        )

        self.assertEqual(len(event.reasons), 2)

    def test_reject_empty_or_duplicate_package_reasons(self) -> None:
        for reasons in (
            (),
            (
                PackageReconciliationReason.ROUTE_PROGRESS_ADVANCED,
                PackageReconciliationReason.ROUTE_PROGRESS_ADVANCED,
            ),
        ):
            with self.subTest(reasons=reasons), self.assertRaises(ValueError):
                _package_event(reasons)

    def test_reject_empty_or_duplicate_route_reasons(self) -> None:
        for reasons in (
            (),
            (
                RouteReconciliationReason.BEFORE_SCHEDULED_DEPARTURE,
                RouteReconciliationReason.BEFORE_SCHEDULED_DEPARTURE,
            ),
        ):
            with self.subTest(reasons=reasons), self.assertRaises(ValueError):
                RouteStateReconciled(
                    route_id=3,
                    previous_status=RouteStatus.IN_PROGRESS,
                    new_status=RouteStatus.SCHEDULED,
                    departure_time=datetime(2026, 7, 10, 14, 0),
                    expected_completion_time=datetime(2026, 7, 10, 18, 0),
                    reasons=reasons,
                    occurred_at=datetime(2026, 7, 10, 12, 0),
                )


def _package_event(
    reasons: tuple[PackageReconciliationReason, ...],
) -> PackageStateReconciled:
    """Build a package reconciliation event with configurable reasons."""
    return PackageStateReconciled(
        package_id=7,
        route_id=3,
        previous_status=ItemStatus.TODO,
        new_status=ItemStatus.IN_PROGRESS,
        previous_location=LocationCode("SYD"),
        new_location=LocationCode("MEL"),
        previous_expected_arrival=None,
        new_expected_arrival=datetime(2026, 7, 10, 14, 0),
        scheduled_pickup_time=datetime(2026, 7, 10, 10, 0),
        scheduled_delivery_time=datetime(2026, 7, 10, 14, 0),
        reasons=reasons,
        occurred_at=datetime(2026, 7, 10, 12, 0),
    )
