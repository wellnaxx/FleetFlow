"""Tests for runtime world-state advancement event recording."""

import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.events.reconciliation_events import RouteStateReconciled
from src.application.events.world_state_events import WorldStateAdvanced
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.use_cases.state.advance_world_state import AdvanceWorldStateUseCase
from src.domain.enums.route_status import RouteStatus

NOW = datetime(2025, 1, 1, 12, 0)


class AdvanceWorldStateUseCaseShould(unittest.TestCase):
    """Validate application-event recording around heartbeat reconciliation."""

    def test_record_reconciliation_events_before_world_state_advanced(self) -> None:
        reconciliation_event = RouteStateReconciled(
            route_id=30,
            previous_status=RouteStatus.IN_PROGRESS,
            new_status=RouteStatus.PLANNED,
            departure_time=None,
            expected_completion_time=None,
            reason=RouteReconciliationReason.MISSING_DEPARTURE_TIME,
            occurred_at=NOW,
        )
        heartbeat_service = MagicMock()
        heartbeat_service.advance.return_value = HeartbeatSummary(
            mutated_routes=(MagicMock(),),
            mutated_packages=(),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
            reconciliation_events=(reconciliation_event,),
        )
        use_case = AdvanceWorldStateUseCase(heartbeat_service)

        result = use_case.execute(now=NOW)

        self.assertIs(result, heartbeat_service.advance.return_value)
        self.assertEqual(len(use_case.pending_events), 2)
        self.assertIs(use_case.pending_events[0], reconciliation_event)
        advanced_event = cast(WorldStateAdvanced, use_case.pending_events[1])
        self.assertIsInstance(advanced_event, WorldStateAdvanced)
        self.assertEqual(advanced_event.event_version, 2)
        self.assertEqual(advanced_event.trucks_reconciled, 0)
        heartbeat_service.advance.assert_called_once_with(now=NOW)

    def test_record_no_events_when_heartbeat_changes_nothing(self) -> None:
        heartbeat_service = MagicMock()
        heartbeat_service.advance.return_value = HeartbeatSummary(
            mutated_routes=(),
            mutated_packages=(),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
        )
        use_case = AdvanceWorldStateUseCase(heartbeat_service)

        use_case.execute(now=NOW)

        self.assertEqual(use_case.pending_events, ())


if __name__ == "__main__":
    unittest.main()
