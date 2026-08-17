"""Execution-local application events and tracked domain event recorders."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from src.application.eventing.collector import EventRecorder
from src.application.events.base import ApplicationEvent
from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin


class EventRecorderScope:
    """Collect event recorders belonging to one message execution.

    The scope is itself the recorder for application events. Domain events
    remain buffered by the entities that produced them; the scope retains one
    reference to each entity in first-registration order. Context-local
    binding isolates concurrent and nested message executions.
    """

    def __init__(self) -> None:
        """Initialize empty application-event and domain-recorder buffers."""
        self._pending_events: list[ApplicationEvent] = []
        self._domain_recorders: dict[int, DomainEventRecorderMixin] = {}

    def record_application_event(self, event: ApplicationEvent) -> None:
        """Append an application event to this execution.

        Args:
            event: Application event emitted by the executing workflow.
        """
        self._pending_events.append(event)

    @property
    def pending_events(self) -> tuple[ApplicationEvent, ...]:
        """Return scoped application events in recording order."""
        return tuple(self._pending_events)

    def clear_events(self) -> None:
        """Clear scoped application events after successful publication.

        Domain events are not cleared here. The event collector receives each
        tracked domain recorder separately and clears its snapshot directly.
        """
        self._pending_events.clear()

    def track_domain_recorder(self, recorder: DomainEventRecorderMixin) -> None:
        """Track one domain recorder by object identity.

        Repeated registration of the same object is idempotent and preserves
        its original ordering.

        Args:
            recorder: Domain entity whose pending events belong to this
                execution.
        """
        self._domain_recorders.setdefault(id(recorder), recorder)

    def event_recorders(self) -> tuple[EventRecorder, ...]:
        """Return this application recorder followed by domain recorders."""
        return (self, *self._domain_recorders.values())


_current_recorder_scope: ContextVar[EventRecorderScope | None] = ContextVar(
    "current_event_recorder_scope",
    default=None,
)


def get_event_recorder_scope() -> EventRecorderScope:
    """Return the recorder scope bound to the current execution.

    Returns:
        Currently bound event-recorder scope.

    Raises:
        RuntimeError: If the caller is outside scoped message execution.
    """
    scope = _current_recorder_scope.get()
    if scope is None:
        raise RuntimeError("No event recorder scope is bound.")
    return scope


def get_optional_event_recorder_scope() -> EventRecorderScope | None:
    """Return the current scope, or ``None`` when no scope is bound."""
    return _current_recorder_scope.get()


@contextmanager
def bind_event_recorder_scope() -> Generator[EventRecorderScope]:
    """Bind a fresh recorder scope and restore the previous binding.

    Nested bindings receive independent scopes. Leaving any binding restores
    its predecessor even when execution raises.

    Yields:
        Fresh scope bound for the duration of the managed block.
    """
    scope = EventRecorderScope()
    token = _current_recorder_scope.set(scope)
    try:
        yield scope
    finally:
        _current_recorder_scope.reset(token)


def record_application_event(event: ApplicationEvent) -> None:
    """Record an application event in the current execution scope.

    Args:
        event: Application event emitted by the current workflow.

    Raises:
        RuntimeError: If no event-recorder scope is bound.
    """
    get_event_recorder_scope().record_application_event(event)


def track_domain_recorder(recorder: DomainEventRecorderMixin) -> None:
    """Track a domain event recorder in the current execution scope.

    Args:
        recorder: Domain entity whose pending events belong to the execution.

    Raises:
        RuntimeError: If no event-recorder scope is bound.
    """
    get_event_recorder_scope().track_domain_recorder(recorder)
