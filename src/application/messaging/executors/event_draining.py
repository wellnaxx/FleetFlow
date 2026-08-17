"""Message-executor decorator providing scoped event publication."""

import logging

from src.application.eventing.collector import EventCollector
from src.application.eventing.recorder_scope import bind_event_recorder_scope
from src.application.messaging.executors.protocols import MessageExecutor

logger = logging.getLogger(__name__)


class EventDrainingExecutor[M, R]:
    """Execute one message and drain its execution-local event recorders.

    Successful execution publishes scoped application events followed by
    events from domain recorders in registration order. Publication failures
    on this path propagate to the caller.

    If the delegate fails, one best-effort publication attempt preserves
    denial and failure events. A publication failure during that attempt is
    logged, and the original delegate exception is re-raised unchanged. Scope
    binding is restored on every path, including nested execution.
    """

    def __init__(
        self,
        delegate: MessageExecutor[M, R],
        event_collector: EventCollector,
    ) -> None:
        """Initialize the event-aware execution decorator.

        Args:
            delegate: Command or query executor performing application work.
            event_collector: Collector that envelopes, publishes, and clears
                events belonging to each execution.
        """
        self._delegate = delegate
        self._event_collector = event_collector

    def execute(self, message: M) -> R:
        """Execute a message inside a fresh event-recorder scope.

        Args:
            message: Typed command or query accepted by the delegate.

        Returns:
            Exact result returned by the delegate.

        Raises:
            Exception: Re-raises delegate failures unchanged. If execution
                succeeds, publication failures propagate from the collector.
        """
        with bind_event_recorder_scope() as scope:
            try:
                result = self._delegate.execute(message)
            except Exception:
                try:
                    self._event_collector.drain(scope.event_recorders())
                except Exception:
                    logger.exception("Failed to publish pending events after execution failure.")
                raise

            self._event_collector.drain(scope.event_recorders())
            return result
