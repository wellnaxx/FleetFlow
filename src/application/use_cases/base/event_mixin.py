from datetime import datetime

from src.application.events.base import ApplicationEvent
from src.shared.event_recorder_mixin import EventRecorderMixin


class ApplicationEventRecorderMixin(EventRecorderMixin[ApplicationEvent]):
    """Marker mixin for use cases that record pending application events."""

    __slots__ = ()

    def record_event(self, event: ApplicationEvent) -> None:
        """Record an application event from cross-cutting infrastructure."""
        self._record_event(event)

    def event_occurred_at(self) -> datetime:
        """Return the timestamp to use for events recorded by infrastructure.

        Use a use-case clock when one is available, falling back to the current
        local time for event-aware objects that do not expose a clock.
        """
        clock = getattr(self, "_clock", None)
        if callable(clock):
            result = clock()
            if isinstance(result, datetime):
                return result
        return datetime.now()
