"""Scoped execution and causally ordered publication for world advancement."""

import logging

from src.application.commands.state.advance_world import AdvanceWorldStateCommand
from src.application.eventing.collector import EventCollector
from src.application.eventing.recorder_scope import bind_event_recorder_scope
from src.application.messaging.executors.protocols import MessageExecutor
from src.application.results.heartbeat_summary_result import HeartbeatSummary

logger = logging.getLogger(__name__)


class WorldStateAdvancementExecutor:
    """Execute world advancement and publish domain events before summaries.

    Heartbeat reconciliation can produce route and package domain events as
    well as reconciliation and aggregate application events. Unlike the
    generic event-draining executor, this executor derives changed domain
    recorders from the successful ``HeartbeatSummary`` and drains those
    recorders before the application-event scope. This preserves heartbeat's
    required causal publication order.
    """

    def __init__(
        self,
        delegate: MessageExecutor[AdvanceWorldStateCommand, HeartbeatSummary],
        event_collector: EventCollector,
    ) -> None:
        """Initialize the dedicated advancement executor.

        Args:
            delegate: World-state advancement workflow to execute.
            event_collector: Collector that publishes and clears heartbeat
                domain and application events.
        """
        self._delegate = delegate
        self._event_collector = event_collector

    def execute(self, command: AdvanceWorldStateCommand, /) -> HeartbeatSummary:
        """Execute one advancement and drain its events in causal order.

        Args:
            command: Fieldless internal advancement request.

        Returns:
            Exact heartbeat summary returned by the delegated workflow.

        Raises:
            Exception: Re-raises delegate failures unchanged. Publication
                failures propagate after successful execution. A publication
                failure while handling a delegate failure is logged without
                replacing the original exception.
        """
        with bind_event_recorder_scope() as scope:
            try:
                summary = self._delegate.execute(command)
            except Exception:
                try:
                    self._event_collector.drain((scope,))
                except Exception:
                    logger.exception("Failed to publish pending world-advancement events.")
                raise

            self._event_collector.drain((*summary.event_recorders, scope))
            return summary
