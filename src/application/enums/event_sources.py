"""Execution origins for event-producing workflows."""

from enum import StrEnum


class EventSource(StrEnum):
    """Execution origins that initiate event-producing workflows."""

    HTTP = "HTTP"
    CLI = "CLI"
    STARTUP = "STARTUP"
    HEARTBEAT = "HEARTBEAT"
    SYSTEM = "SYSTEM"
