import contextlib
import json
import os
import unittest
import uuid
from typing import Any

from src.adapters.driven.persistence.json.paths import DATA_DIR
from src.adapters.driven.persistence.json.world_state_persistence import JsonWorldStatePersistence
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
)


class JsonWorldStatePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.persistence = JsonWorldStatePersistence()

    def make_snapshot(self, *, schema_version: int = 2) -> WorldStateSnapshot:
        return WorldStateSnapshot(
            schema_version=schema_version,
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
                trucks=(),
            ),
        )

    def test_write_uses_canonical_nested_world_schema(self) -> None:
        snapshot = self.make_snapshot()
        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            written_path = self.persistence.write(path, snapshot)

            with open(written_path, encoding="utf-8") as file:
                raw = json.load(file)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertEqual(
            raw,
            {
                "schema_version": 2,
                "world": {
                    "counters": {
                        "next_customer_id": 3,
                        "next_package_id": 4,
                        "next_route_id": 5,
                    },
                    "customers": [
                        {
                            "customer_id": 1,
                            "name": "Alice",
                            "email": "alice@example.com",
                            "phone": "0412345678",
                        }
                    ],
                    "packages": [
                        {
                            "package_id": 2,
                            "start": "A",
                            "end": "B",
                            "weight": 3.5,
                            "customer_id": 1,
                            "route_id": 7,
                        }
                    ],
                    "routes": [
                        {
                            "route_id": 7,
                            "locations": ["A", "B"],
                            "departure_time": "2025-01-01T10:00:00",
                            "truck_vehicle_id": 1001,
                            "package_ids": [2],
                        }
                    ],
                    "trucks": [],
                },
                "users": None,
            },
        )
        self.assertNotIn("counters", raw)
        self.assertNotIn("customers", raw)
        self.assertNotIn("packages", raw)
        self.assertNotIn("routes", raw)

    def test_read_supports_nested_world_schema(self) -> None:
        snapshot = self.make_snapshot()
        raw = {
            "schema_version": 2,
            "world": {
                "counters": {
                    "next_customer_id": 3,
                    "next_package_id": 4,
                    "next_route_id": 5,
                },
                "customers": [
                    {
                        "customer_id": 1,
                        "name": "Alice",
                        "email": "alice@example.com",
                        "phone": "0412345678",
                    }
                ],
                "packages": [
                    {
                        "package_id": 2,
                        "start": "A",
                        "end": "B",
                        "weight": 3.5,
                        "customer_id": 1,
                        "route_id": 7,
                    }
                ],
                "routes": [
                    {
                        "route_id": 7,
                        "locations": ["A", "B"],
                        "departure_time": "2025-01-01T10:00:00",
                        "truck_vehicle_id": 1001,
                        "package_ids": [2],
                    }
                ],
            },
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            _read_path, loaded = self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertEqual(loaded, snapshot)

    def test_read_supports_truck_snapshots(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=2,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
                trucks=(
                    TruckSnapshot(
                        vehicle_id=1001,
                        status="Free",
                        current_location="MEL",
                        route_id=None,
                        busy_from=None,
                        busy_until=None,
                        in_transit_to=None,
                    ),
                    TruckSnapshot(
                        vehicle_id=1002,
                        status="On the way",
                        current_location="SYD",
                        route_id=7,
                        busy_from="2025-01-01T10:00:00",
                        busy_until="2025-01-01T11:00:00",
                        in_transit_to="MEL",
                    ),
                ),
            ),
        )
        raw = {
            "schema_version": 2,
            "world": {
                "counters": {
                    "next_customer_id": 1,
                    "next_package_id": 1,
                    "next_route_id": 1,
                },
                "customers": [],
                "packages": [],
                "routes": [],
                "trucks": [
                    {
                        "vehicle_id": 1001,
                        "status": "Free",
                        "current_location": "MEL",
                        "route_id": None,
                        "busy_from": None,
                        "busy_until": None,
                        "in_transit_to": None,
                    },
                    {
                        "vehicle_id": 1002,
                        "status": "On the way",
                        "current_location": "SYD",
                        "route_id": 7,
                        "busy_from": "2025-01-01T10:00:00",
                        "busy_until": "2025-01-01T11:00:00",
                        "in_transit_to": "MEL",
                    },
                ],
            },
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            _read_path, loaded = self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertEqual(loaded, snapshot)

    def test_read_supports_legacy_flat_world_schema(self) -> None:
        snapshot = self.make_snapshot(schema_version=1)
        raw = {
            "schema_version": 1,
            "counters": {
                "next_customer_id": 3,
                "next_package_id": 4,
                "next_route_id": 5,
            },
            "customers": [
                {
                    "customer_id": 1,
                    "name": "Alice",
                    "email": "alice@example.com",
                    "phone": "0412345678",
                }
            ],
            "packages": [
                {
                    "package_id": 2,
                    "start": "A",
                    "end": "B",
                    "weight": 3.5,
                    "customer_id": 1,
                    "route_id": 7,
                }
            ],
            "routes": [
                {
                    "route_id": 7,
                    "locations": ["A", "B"],
                    "departure_time": "2025-01-01T10:00:00",
                    "truck_vehicle_id": 1001,
                    "package_ids": [2],
                }
            ],
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            read_path, loaded = self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertTrue(read_path.endswith(filename))
        self.assertEqual(loaded, snapshot)

    def test_read_missing_file_raises_world_state_file_not_found(self) -> None:
        filename = f"missing-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)
        try:
            with self.assertRaises(WorldStateFileNotFoundError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("State file not found", str(ctx.exception))

    def test_write_then_read_round_trips_snapshot(self) -> None:
        snapshot = self.make_snapshot()
        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            written_path = self.persistence.write(path, snapshot)
            read_path, loaded = self.persistence.read(written_path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertEqual(read_path, written_path)
        self.assertEqual(loaded, snapshot)

    def test_read_malformed_json_raises_world_state_corruption_error(self) -> None:
        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write("{ bad json")

            with self.assertRaises(WorldStateCorruptionError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))

    def test_read_malformed_truck_snapshot_raises_world_state_corruption_error(self) -> None:
        malformed_truck_cases = (
            ("vehicle_id", {"vehicle_id": True}),
            ("status", {"status": None}),
            ("current_location", {"current_location": 100}),
            ("route_id", {"route_id": "1"}),
            ("busy_from", {"busy_from": 100}),
            ("busy_until", {"busy_until": 100}),
            ("in_transit_to", {"in_transit_to": 100}),
        )

        for label, override in malformed_truck_cases:
            with self.subTest(label=label):
                truck = {
                    "vehicle_id": 1001,
                    "status": "Free",
                    "current_location": "MEL",
                    "route_id": None,
                    "busy_from": None,
                    "busy_until": None,
                    "in_transit_to": None,
                }
                truck.update(override)
                raw = {
                    "schema_version": 1,
                    "world": {
                        "counters": {
                            "next_customer_id": 1,
                            "next_package_id": 1,
                            "next_route_id": 1,
                        },
                        "customers": [],
                        "packages": [],
                        "routes": [],
                        "trucks": [truck],
                    },
                }

                filename = f"world-state-{uuid.uuid4().hex}.json"
                path = os.path.join(DATA_DIR, filename)
                try:
                    with open(path, "w", encoding="utf-8") as file:
                        json.dump(raw, file)

                    with self.assertRaises(WorldStateCorruptionError) as ctx:
                        self.persistence.read(path)
                finally:
                    with contextlib.suppress(OSError):
                        os.remove(path)

                self.assertIn("Malformed world state JSON", str(ctx.exception))

    def test_read_malformed_payload_raises_world_state_corruption_error(self) -> None:
        raw: dict[str, int | dict[str, dict[str, int] | str | list[Any]]] = {
            "schema_version": 1,
            "world": {
                "counters": {
                    "next_customer_id": 3,
                    "next_package_id": 4,
                    "next_route_id": 5,
                },
                "customers": "not-a-list",
                "packages": [],
                "routes": [],
            },
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            with self.assertRaises(WorldStateCorruptionError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))

    def test_read_payload_without_world_or_legacy_sections_raises_world_state_corruption_error(self) -> None:
        raw = {
            "schema_version": 1,
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            with self.assertRaises(WorldStateCorruptionError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))
