from src.application.events.base import ApplicationEvent
from src.shared.event_recorder_mixin import EventRecorderMixin


class ApplicationEventRecorderMixin(EventRecorderMixin[ApplicationEvent]):
    """Marker mixin for use cases that record pending application events."""

    __slots__ = ()
