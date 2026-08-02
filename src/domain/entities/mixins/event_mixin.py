from src.domain.events.base import DomainEvent
from src.shared.event_recorder_mixin import EventRecorderMixin


class DomainEventRecorderMixin(EventRecorderMixin[DomainEvent]):
    """Marker mixin class that provides event recording functionality for entities."""

    __slots__ = ()
