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
    WorldSnapshotData,
    WorldStateSnapshot,
)


class JsonWorldStatePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.persistence = JsonWorldStatePersistence()

    def make_snapshot(self) -> WorldStateSnapshot:
        return WorldStateSnapshot(
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
                "schema_version": 1,
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
            "schema_version": 1,
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

    def test_read_supports_legacy_flat_world_schema(self) -> None:
        snapshot = self.make_snapshot()
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

    def test_read_malformed_json_raises_value_error(self) -> None:
        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write("{ bad json")

            with self.assertRaises(ValueError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))

    def test_read_malformed_payload_raises_value_error(self) -> None:
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

            with self.assertRaises(ValueError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))

    def test_read_payload_without_world_or_legacy_sections_raises_value_error(self) -> None:
        raw = {
            "schema_version": 1,
        }

        filename = f"world-state-{uuid.uuid4().hex}.json"
        path = os.path.join(DATA_DIR, filename)

        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump(raw, file)

            with self.assertRaises(ValueError) as ctx:
                self.persistence.read(path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(path)

        self.assertIn("Malformed world state JSON", str(ctx.exception))