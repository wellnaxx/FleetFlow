from datetime import datetime

from src.application.eventing.recorder_scope import get_optional_event_recorder_scope
from src.application.events.base import ApplicationEvent
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.shared.event_recorder_mixin import EventRecorderMixin


class ApplicationEventRecorderMixin(EventRecorderMixin[ApplicationEvent]):
    """Record application events through scoped or legacy storage.

    Bus-migrated workflows write into an execution-local recorder scope.
    Legacy adapters execute without a scope and retain events on the use-case
    instance for explicit drainage. An event is written to exactly one
    destination.
    """

    __slots__ = ()

    def record_event(self, event: ApplicationEvent) -> None:
        """Record an application event using the active execution model.

        Args:
            event: Event emitted by the workflow or authorization
                infrastructure.
        """
        scope = get_optional_event_recorder_scope()

        if scope is None:
            self._record_event(event)
            return

        scope.record_application_event(event)

    def track_domain_recorder(self, recorder: DomainEventRecorderMixin) -> None:
        """Register a mutated domain entity with the active execution scope.

        Bus-executed workflows use this hook to make domain events available
        to the scoped event-draining executor. During legacy direct execution,
        no scope exists and adapters retain responsibility for draining the
        returned entities explicitly.

        Args:
            recorder: Domain entity whose pending events were produced by the
                current workflow.
        """
        scope = get_optional_event_recorder_scope()
        if scope is not None:
            scope.track_domain_recorder(recorder)

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
