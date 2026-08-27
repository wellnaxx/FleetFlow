"""Use case for advancing runtime world state."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.commands.state.advance_world import AdvanceWorldStateCommand
from src.application.events.world_state_events import WorldStateAdvanced
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.heartbeat_service import HeartbeatService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin

logger = logging.getLogger(__name__)


class AdvanceWorldStateUseCase(BaseUseCase[HeartbeatSummary], ApplicationEventRecorderMixin):
    """Advance world state and record reconciliation and heartbeat events."""

    def __init__(
        self,
        heartbeat_service: HeartbeatService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            heartbeat_service: Service that performs reconciliation.
            clock: App-local business clock sampled once per advancement.
        """
        self._heartbeat_service = heartbeat_service
        self._clock = clock

        self._pending_events = []

    def execute(self, command: AdvanceWorldStateCommand) -> HeartbeatSummary:
        """Advance route, truck, and package state.

        Args:
            command: Fieldless request to run one heartbeat reconciliation.

        Returns:
            Summary of persisted reconciliation changes. Direct reconciliation
            events from the summary are recorded first, followed by one
            ``WorldStateAdvanced`` event when any state changed.

        Raises:
            Exception: Propagates reconciliation, persistence, and rollback
                failures from the heartbeat service unchanged.
        """
        del command
        now = self._clock()
        summary = self._heartbeat_service.advance(now=now)

        for event in summary.reconciliation_events:
            self.record_event(event)

        if summary.state_changed:
            self.record_event(
                WorldStateAdvanced(
                    occurred_at=now,
                    routes_updated=summary.routes_updated,
                    packages_updated=summary.packages_updated,
                    trucks_moved=summary.trucks_moved,
                    trucks_released=summary.trucks_released,
                    trucks_reconciled=summary.trucks_reconciled,
                )
            )

            logger.info(
                "Advanced world state: routes=%d, packages=%d, trucks_moved=%d, "
                "trucks_released=%d, trucks_reconciled=%d.",
                summary.routes_updated,
                summary.packages_updated,
                summary.trucks_moved,
                summary.trucks_released,
                summary.trucks_reconciled,
            )
        else:
            logger.debug("Advanced world state with no state changes.")
        return summary
