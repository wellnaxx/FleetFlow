"""Use case for advancing runtime world state."""

import logging
from datetime import datetime

from src.application.events.world_state_events import WorldStateAdvanced
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.heartbeat_service import HeartbeatService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin

logger = logging.getLogger(__name__)


class AdvanceWorldStateUseCase(BaseUseCase[HeartbeatSummary], ApplicationEventRecorderMixin):
    """Advance runtime world state and record a heartbeat event when it changes."""

    def __init__(
        self,
        heartbeat_service: HeartbeatService,
    ) -> None:
        """Initialize the use case.

        Args:
            heartbeat_service: Service that performs reconciliation.
        """
        self._heartbeat_service = heartbeat_service

        self._pending_events = []

    def execute(self, now: datetime | None = None) -> HeartbeatSummary:
        """Advance route, truck, and package state.

        Args:
            now: Optional clock override for deterministic execution.

        Returns:
            A summary of the changes applied during the heartbeat, including
            whether any state was mutated at all. A ``WorldStateAdvanced``
            event is recorded only when the heartbeat changes runtime state.
        """
        summary = self._heartbeat_service.advance(now=now)
        if summary.state_changed:
            self._record_event(
                WorldStateAdvanced(
                    occurred_at=now or datetime.now(),
                    routes_updated=summary.routes_updated,
                    packages_updated=summary.packages_updated,
                    trucks_moved=summary.trucks_moved,
                    trucks_released=summary.trucks_released,
                )
            )

            logger.info(
                "Advanced world state: routes=%d, packages=%d, trucks_moved=%d, trucks_released=%d.",
                summary.routes_updated,
                summary.packages_updated,
                summary.trucks_moved,
                summary.trucks_released,
            )
        else:
            logger.debug("Advanced world state with no state changes.")
        return summary
