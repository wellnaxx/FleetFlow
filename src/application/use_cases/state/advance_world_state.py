from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.heartbeat_service import HeartbeatService


class AdvanceWorldStateUseCase:
    def __init__(self, heartbeat_service: HeartbeatService) -> None:
        self._heartbeat_service = heartbeat_service

    def execute(self, now: datetime | None = None) -> HeartbeatSummary:
        return self._heartbeat_service.advance(now=now)
