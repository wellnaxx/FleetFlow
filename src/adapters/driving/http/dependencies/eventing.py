"""FastAPI dependencies for event publication infrastructure."""

import logging
from collections.abc import Callable

from src.application.eventing.collector import EventCollector
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.composition.runtime import get_container

logger = logging.getLogger(__name__)


def get_event_collector() -> EventCollector:
    """Return the shared event collector from the application container."""
    return get_container().event_collector


def execute_and_drain_events[R](
    *,
    recorder: ApplicationEventRecorderMixin,
    event_collector: EventCollector,
    action: Callable[[], R],
) -> R:
    """Run an HTTP workflow and publish application events from its recorder.

    If the workflow raises after recording rejection or failure events, event
    publication is attempted and the original exception is re-raised for the
    normal FastAPI exception handlers.

    Args:
        recorder: Application-event recorder that may contain pending events.
        event_collector: Collector used to publish and clear pending events.
        action: HTTP workflow operation to execute before event drainage.

    Returns:
        The value returned by ``action``.

    Raises:
        Exception: Re-raises any exception from ``action``. On the success
            path, event publication failures propagate from ``event_collector``.
    """
    try:
        result = action()
    except Exception:
        try:
            event_collector.drain((recorder,))
        except Exception:
            logger.exception("Failed to publish pending events after HTTP request failure.")
        raise

    event_collector.drain((recorder,))
    return result
