from enum import StrEnum


class EventSource(StrEnum):
    """Sources of events in the application."""

    HTTP = "HTTP"
    CLI = "CLI"
    STARTUP = "STARTUP"
    HEARTBEAT = "HEARTBEAT"
    SYSTEM = "SYSTEM"
