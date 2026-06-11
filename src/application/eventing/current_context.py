"""Context-local access to the current event-producing workflow."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from src.application.eventing.context import EventContext
from src.application.eventing.envelope import EventEnvelope
from src.shared.event import Event

_current_event_context: ContextVar[EventContext | None] = ContextVar(
    "current_event_context",
    default=None,
)


def get_event_context() -> EventContext:
    """Return the context bound to the current execution flow.

    Returns:
        Currently bound event context.

    Raises:
        RuntimeError: If no event context is bound.
    """
    context = _current_event_context.get()
    if context is None:
        raise RuntimeError("No event context is bound.")
    return context


def get_optional_event_context() -> EventContext | None:
    """Return the currently bound context, or `None` when unbound."""
    return _current_event_context.get()


@contextmanager
def bind_event_context(context: EventContext) -> Generator[None]:
    """Bind a context for one workflow and restore the previous binding.

    Args:
        context: Event context to expose inside the managed block.

    Yields:
        Control while the supplied context is bound.
    """
    token = _current_event_context.set(context)
    try:
        yield
    finally:
        _current_event_context.reset(token)


def envelope_event[E: Event](event: E) -> EventEnvelope[E]:
    """Wrap an event using the context bound to this execution flow.

    Args:
        event: Domain or application event to enrich.

    Returns:
        Event envelope containing the current workflow metadata.

    Raises:
        RuntimeError: If no event context is bound.
    """
    return get_event_context().wrap(event)
