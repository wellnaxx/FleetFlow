"""Use case for advancing runtime world state."""

from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.heartbeat_service import HeartbeatService
from src.application.use_cases.base.base_use_case import BaseUseCase


class AdvanceWorldStateUseCase(BaseUseCase[HeartbeatSummary]):
    """Advance the runtime world state using the heartbeat service."""

    def __init__(self, heartbeat_service: HeartbeatService) -> None:
        """Initialize the use case.

        Args:
            heartbeat_service: Service that performs reconciliation.
        """
        self._heartbeat_service = heartbeat_service

    def execute(self, now: datetime | None = None) -> HeartbeatSummary:
        """Advance route, truck, and package state.

        Args:
            now: Optional clock override for deterministic execution.

        Returns:
            A summary of the changes applied during the heartbeat, including
            whether any state was mutated at all.
        """
        return self._heartbeat_service.advance(now=now)
