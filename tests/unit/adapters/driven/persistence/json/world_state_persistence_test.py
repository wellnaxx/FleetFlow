import contextlib
import os
import unittest
import uuid

from src.adapters.driven.persistence.json.paths import DATA_DIR
from src.adapters.driven.persistence.json.world_state_persistence import JsonWorldStatePersistence
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)


class JsonWorldStatePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.persistence = JsonWorldStatePersistence()

    def test_write_and_read_round_trip_snapshot(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(3, 4, 5),
                customers=(
                    CustomerSnapshot(
                        customer_id=1,
                        name="Alice",
                        email="alice@example.com",
                        phone="0412345678",
                    ),
                ),
                packages=(
                    PackageSnapshot(
                        package_id=2,
                        start="A",
                        end="B",
                        weight=3.5,
                        customer_id=1,
                        route_id=7,
                    ),
                ),
                routes=(
                    RouteSnapshot(
                        route_id=7,
                        locations=("A", "B"),
                        departure_time="2025-01-01T10:00:00",
                        truck_vehicle_id=1001,
                        package_ids=(2,),
                    ),
                ),
            ),
        )

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            written_path = self.persistence.write(path, snapshot)
            read_path, loaded = self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertEqual(read_path, written_path)
        self.assertEqual(loaded, snapshot)

    def test_read_missing_file_raises_value_error(self) -> None:
        filename = f"missing-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            with self.assertRaises(ValueError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("State file not found", str(ctx.exception))
