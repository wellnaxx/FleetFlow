"""Tests for causally ordered world-state advancement execution."""

import unittest
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock

from src.application.commands.state.advance_world import AdvanceWorldStateCommand
from src.application.eventing.collector import EventCollector, EventRecorder
from src.application.eventing.recorder_scope import (
    EventRecorderScope,
    get_optional_event_recorder_scope,
    record_application_event,
)
from src.application.events.base import ApplicationEvent
from src.application.messaging.executors.world_state_advancement import WorldStateAdvancementExecutor
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.domain.entities.delivery_route import DeliveryRoute

NOW = datetime(2026, 8, 27, 12, 0)


@dataclass(frozen=True, slots=True, kw_only=True)
class SampleApplicationEvent(ApplicationEvent):
    """Application event emitted by an advancement-test delegate."""

    label: str


class AdvancementDelegate:
    """Execute a configurable callback and retain received commands."""

    def __init__(self, callback: Callable[[AdvanceWorldStateCommand], HeartbeatSummary]) -> None:
        self._callback = callback
        self.commands: list[AdvanceWorldStateCommand] = []

    def execute(self, command: AdvanceWorldStateCommand, /) -> HeartbeatSummary:
        """Record and execute one advancement command."""
        self.commands.append(command)
        return self._callback(command)


class WorldStateAdvancementExecutorShould(unittest.TestCase):
    """Verify result propagation, event order, and exception precedence."""

    def test_return_exact_summary_and_drain_domain_recorders_before_scope(self) -> None:
        application_event = SampleApplicationEvent(occurred_at=NOW, label="advanced")
        first_route = cast(DeliveryRoute, MagicMock())
        second_route = cast(DeliveryRoute, MagicMock())
        summary = self._summary(mutated_routes=(first_route, second_route, first_route))

        def advance(command: AdvanceWorldStateCommand) -> HeartbeatSummary:
            del command
            record_application_event(application_event)
            return summary

        delegate = AdvancementDelegate(advance)
        collector_mock = MagicMock(spec=EventCollector)
        executor = WorldStateAdvancementExecutor(
            delegate,
            cast(EventCollector, collector_mock),
        )
        command = AdvanceWorldStateCommand()

        result = executor.execute(command)

        self.assertIs(result, summary)
        self.assertEqual(delegate.commands, [command])
        collector_mock.drain.assert_called_once()
        recorders = tuple(cast(tuple[EventRecorder, ...], collector_mock.drain.call_args.args[0]))
        self.assertEqual(recorders[:2], (first_route, second_route))
        scope = cast(EventRecorderScope, recorders[2])
        self.assertEqual(scope.pending_events, (application_event,))
        self.assertIsNone(get_optional_event_recorder_scope())

    def test_unchanged_summary_drains_only_application_scope(self) -> None:
        summary = self._summary()
        collector_mock = MagicMock(spec=EventCollector)
        executor = WorldStateAdvancementExecutor(
            AdvancementDelegate(lambda command: summary),
            cast(EventCollector, collector_mock),
        )

        executor.execute(AdvanceWorldStateCommand())

        recorders = tuple(cast(tuple[EventRecorder, ...], collector_mock.drain.call_args.args[0]))
        self.assertEqual(len(recorders), 1)
        self.assertIsInstance(recorders[0], EventRecorderScope)

    def test_propagate_publication_failure_after_success(self) -> None:
        publication_error = RuntimeError("publication failed")
        collector_mock = MagicMock(spec=EventCollector)
        collector_mock.drain.side_effect = publication_error
        executor = WorldStateAdvancementExecutor(
            AdvancementDelegate(lambda command: self._summary()),
            cast(EventCollector, collector_mock),
        )

        with self.assertRaises(RuntimeError) as raised:
            executor.execute(AdvanceWorldStateCommand())

        self.assertIs(raised.exception, publication_error)
        self.assertIsNone(get_optional_event_recorder_scope())

    def test_failure_drains_application_scope_and_reraises_original_exception(self) -> None:
        delegate_error = ValueError("advancement failed")
        failure_event = SampleApplicationEvent(occurred_at=NOW, label="failed")

        def fail(command: AdvanceWorldStateCommand) -> HeartbeatSummary:
            del command
            record_application_event(failure_event)
            raise delegate_error

        collector_mock = MagicMock(spec=EventCollector)
        executor = WorldStateAdvancementExecutor(
            AdvancementDelegate(fail),
            cast(EventCollector, collector_mock),
        )

        with self.assertRaises(ValueError) as raised:
            executor.execute(AdvanceWorldStateCommand())

        self.assertIs(raised.exception, delegate_error)
        recorders = tuple(cast(tuple[EventRecorder, ...], collector_mock.drain.call_args.args[0]))
        self.assertEqual(len(recorders), 1)
        scope = cast(EventRecorderScope, recorders[0])
        self.assertEqual(scope.pending_events, (failure_event,))

    def test_log_failure_publication_error_without_replacing_delegate_error(self) -> None:
        delegate_error = ValueError("advancement failed")
        collector_mock = MagicMock(spec=EventCollector)
        collector_mock.drain.side_effect = RuntimeError("publication failed")

        def fail(command: AdvanceWorldStateCommand) -> HeartbeatSummary:
            del command
            raise delegate_error

        executor = WorldStateAdvancementExecutor(
            AdvancementDelegate(fail),
            cast(EventCollector, collector_mock),
        )

        with (
            self.assertLogs(
                "src.application.messaging.executors.world_state_advancement",
                level="ERROR",
            ) as logs,
            self.assertRaises(ValueError) as raised,
        ):
            executor.execute(AdvanceWorldStateCommand())

        self.assertIs(raised.exception, delegate_error)
        self.assertTrue(any("pending world-advancement events" in entry for entry in logs.output))
        self.assertIsNone(get_optional_event_recorder_scope())

    @staticmethod
    def _summary(
        *,
        mutated_routes: tuple[DeliveryRoute, ...] = (),
    ) -> HeartbeatSummary:
        """Return a heartbeat summary with optional mutated route recorders."""
        return HeartbeatSummary(
            mutated_routes=mutated_routes,
            mutated_packages=(),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
        )


if __name__ == "__main__":
    unittest.main()
