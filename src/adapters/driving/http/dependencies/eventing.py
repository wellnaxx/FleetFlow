"""FastAPI dependencies for event publication infrastructure."""

from src.application.eventing.collector import EventCollector
from src.composition.runtime import get_container


def get_event_collector() -> EventCollector:
    """Return the shared event collector from the application container."""
    return get_container().event_collector
