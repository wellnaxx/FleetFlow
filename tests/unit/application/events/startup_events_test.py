"""Tests for startup application event contracts."""

import unittest
from datetime import datetime

from src.application.events.startup_events import FleetSeeded


class StartupEventShould(unittest.TestCase):
    """Validate derived startup event data."""

    def test_derive_seeded_truck_count_from_identifiers(self) -> None:
        event = FleetSeeded(
            seeded_truck_ids=(1001, 1002, 1003),
            backend="memory",
            occurred_at=datetime(2026, 7, 10, 12, 0),
        )

        self.assertEqual(event.truck_count, 3)
        self.assertEqual(event.event_version, 2)
