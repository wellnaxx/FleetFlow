"""Internal command contract for advancing runtime world state."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.results.heartbeat_summary_result import HeartbeatSummary


@dataclass(frozen=True, slots=True)
class AdvanceWorldStateCommand(Command):
    """Request one heartbeat-driven reconciliation of runtime world state.

    The command intentionally carries no timestamp. The use case obtains one
    app-local business time from its injected clock so internal callers cannot
    choose inconsistent reconciliation and event timestamps.
    """


ADVANCE_WORLD_STATE: Final[CommandKey[AdvanceWorldStateCommand, HeartbeatSummary]] = CommandKey(
    name="advance_world_state",
    command_type=AdvanceWorldStateCommand,
)
