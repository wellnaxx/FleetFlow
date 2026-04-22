import json
import os
import tempfile
from dataclasses import asdict
from typing import Any

from src.adapters.driven.persistence.json.paths import resolve_data_path
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.ports.output.world_state_persistence import WorldStatePersistencePort


class JsonWorldStatePersistence(WorldStatePersistencePort):
    """Persist world-state snapshots as JSON files."""

    def write(self, path: str, snapshot: WorldStateSnapshot) -> str:
        """Serialize and atomically write a world-state snapshot.

        Args:
            path: Target path or filename for the JSON snapshot.
            snapshot: Snapshot payload to serialize.

        Returns:
            The resolved absolute path that was written.

        Raises:
            OSError: If the target file cannot be written.
        """
        abs_path = resolve_data_path(path)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        raw_snapshot = self._raw_from_snapshot(snapshot)

        fd, tmp = tempfile.mkstemp(
            prefix="worldstate.",
            suffix=".json",
            dir=os.path.dirname(abs_path) or ".",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(raw_snapshot, file, indent=2)
            os.replace(tmp, abs_path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

        return abs_path

    def read(self, path: str) -> tuple[str, WorldStateSnapshot]:
        """Read and deserialize a world-state snapshot from JSON.

        Args:
            path: Source path or filename to read.

        Returns:
            A tuple of the resolved absolute path and the deserialized snapshot.

        Raises:
            ValueError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        abs_path = resolve_data_path(path)
        if not os.path.exists(abs_path):
            raise ValueError(f"State file not found: {abs_path}")

        with open(abs_path, encoding="utf-8") as file:
            raw = json.load(file)

        return abs_path, self._snapshot_from_raw(raw)

    def _raw_from_snapshot(self, snapshot: WorldStateSnapshot) -> dict[str, Any]:
        """Convert a snapshot DTO into its persisted JSON shape."""
        return asdict(snapshot)

    def _snapshot_from_raw(self, raw: dict[str, Any]) -> WorldStateSnapshot:
        """Build a snapshot DTO from canonical or legacy JSON payloads."""
        world = raw.get("world")
        if world is None:
            world = {
                "counters": raw.get("counters", {}),
                "customers": raw.get("customers", []),
                "packages": raw.get("packages", []),
                "routes": raw.get("routes", []),
            }

        counters = world.get("counters", {})
        return WorldStateSnapshot(
            schema_version=int(raw.get("schema_version", 1)),
            world=WorldSnapshotData(
                counters=CountersSnapshot(
                    next_customer_id=int(counters.get("next_customer_id", 1)),
                    next_package_id=int(counters.get("next_package_id", 1)),
                    next_route_id=int(counters.get("next_route_id", 1)),
                ),
                customers=tuple(
                    CustomerSnapshot(
                        customer_id=int(customer["customer_id"]),
                        name=str(customer["name"]),
                        email=str(customer.get("email", "")),
                        phone=str(customer.get("phone", "")),
                    )
                    for customer in world.get("customers", [])
                ),
                packages=tuple(
                    PackageSnapshot(
                        package_id=int(package["package_id"]),
                        start=str(package["start"]),
                        end=str(package["end"]),
                        weight=float(package["weight"]),
                        customer_id=int(package["customer_id"]),
                        route_id=int(package["route_id"]) if package.get("route_id") is not None else None,
                    )
                    for package in world.get("packages", [])
                ),
                routes=tuple(
                    RouteSnapshot(
                        route_id=int(route["route_id"]),
                        locations=tuple(str(location) for location in route["locations"]),
                        departure_time=route.get("departure_time"),
                        truck_vehicle_id=int(route["truck_vehicle_id"])
                        if route.get("truck_vehicle_id") is not None
                        else None,
                        package_ids=tuple(int(package_id) for package_id in route.get("package_ids", [])),
                    )
                    for route in world.get("routes", [])
                ),
            ),
        )
