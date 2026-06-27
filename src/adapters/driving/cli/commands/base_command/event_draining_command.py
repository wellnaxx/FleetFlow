import logging
from collections.abc import Callable, Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.eventing.collector import EventCollector, EventRecorder

logger = logging.getLogger(__name__)


class EventDrainingCommand[T](BaseCommand[T]):
    """Mixin for CLI commands that publish pending events after execution.

    Commands use this mixin when their use case records application events.
    On successful execution, pending events are drained normally. If the use
    case raises after recording rejection/failure events, the mixin makes a
    best-effort drain and then re-raises the original exception so CLI error
    handling remains unchanged.
    """

    _event_collector: EventCollector

    def __init__(
        self,
        params: Iterable[str],
        use_case: T,
        event_collector: EventCollector,
    ) -> None:
        """Initialize command dependencies and event collection.

        Args:
            params: Raw string parameters parsed from the CLI.
            use_case: Application use case executed by the command.
            event_collector: Collector used to publish pending events.
        """
        super().__init__(params, use_case)
        self._event_collector = event_collector

    @property
    def event_collector(self) -> EventCollector:
        """Return the collector injected by the command factory."""
        return self._event_collector

    def _run_and_drain[R](
        self,
        recorder: EventRecorder,
        action: Callable[[], R],
    ) -> R:
        """Run an action and drain the recorder's pending events.

        Args:
            recorder: Use case or entity whose pending events should publish.
            action: Operation to execute before draining events.

        Returns:
            Result returned by ``action``.

        Raises:
            Exception: Re-raises failures from ``action``. On the success path,
                event publication failures propagate from the collector.
        """
        try:
            result = action()
        except Exception:
            try:
                self._event_collector.drain((recorder,))
            except Exception:
                logger.exception("Failed to publish pending events after command failure.")
            raise

        self._event_collector.drain((recorder,))
        return result
