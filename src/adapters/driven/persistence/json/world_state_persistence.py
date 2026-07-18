"""JSON persistence adapter for world-state snapshots."""

import json
import logging
import os
import tempfile
from dataclasses import asdict
from typing import Any, cast

from src.adapters.driven.persistence.json.paths import resolve_data_path
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
)
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode
from src.ports.output.world_state_persistence import WorldStatePersistencePort
from src.shared.validation import (
    require_int,
    require_optional_int,
    require_optional_str,
    require_positive_finite_float,
    require_str,
)

logger = logging.getLogger(__name__)


class JsonWorldStatePersistence(WorldStatePersistencePort):
    """Persist world-state snapshots as JSON files."""

    def write(self, path: str, snapshot: WorldStateSnapshot) -> str:
        """Serialize and atomically write a world-state snapshot.

        Args:
            path: Target filename or path.
            snapshot: Snapshot DTO to serialize.

        Returns:
            Resolved absolute path written.

        Raises:
            OSError: If the target file cannot be written.
        """
        abs_path = resolve_data_path(path)
        logger.debug("Writing world-state JSON snapshot to %r.", abs_path)
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

        logger.info("World-state JSON snapshot written to %r.", abs_path)
        return abs_path

    def read(self, path: str) -> tuple[str, WorldStateSnapshot]:
        """Read and deserialize a world-state snapshot from JSON.

        Args:
            path: Source filename or path.

        Returns:
            Resolved absolute path and parsed snapshot DTO.

        Raises:
            WorldStateFileNotFoundError: If the file does not exist.
            WorldStateCorruptionError: If JSON parsing or DTO conversion fails.
            WorldStatePersistenceError: If the file cannot be read.
        """
        abs_path = resolve_data_path(path)
        logger.debug("Reading world-state JSON snapshot from %r.", abs_path)
        if not os.path.exists(abs_path):
            raise WorldStateFileNotFoundError(f"State file not found: {abs_path}")

        try:
            with open(abs_path, encoding="utf-8") as file:
                raw: object = json.load(file)
        except json.JSONDecodeError as exc:
            raise WorldStateCorruptionError(
                f"Malformed world state JSON: {abs_path}", reason=WorldStateCorruptionReason.MALFORMED_JSON
            ) from exc
        except OSError as exc:
            raise WorldStatePersistenceError(f"Could not read world state file: {abs_path}") from exc

        snapshot = self._snapshot_from_raw(raw)

        logger.info("World-state JSON snapshot read from %r.", abs_path)
        return abs_path, snapshot

    def _raw_from_snapshot(self, snapshot: WorldStateSnapshot) -> dict[str, Any]:
        """Convert a snapshot DTO into its persisted JSON shape."""
        return asdict(snapshot)

    def _snapshot_from_raw(self, raw: object) -> WorldStateSnapshot:
        """Build a snapshot DTO from canonical or legacy JSON payloads."""
        try:
            raw_dict = self._require_mapping(raw)
            schema_version = self._require_int(raw_dict, "schema_version")
        except TypeError as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVALID_STRUCTURE
            ) from exc

        if schema_version not in (1, 2):
            raise WorldStateCorruptionError(
                f"Unsupported world state schema version: {schema_version}.",
                reason=WorldStateCorruptionReason.UNSUPPORTED_SCHEMA,
            )

        legacy_sections = ("counters", "customers", "packages", "routes")
        present_legacy_sections = [section for section in legacy_sections if section in raw_dict]

        world_obj = raw_dict.get("world")

        if world_obj is None:
            if schema_version != 1:
                raise WorldStateCorruptionError(
                    "Legacy flat world state payload is only supported for schema version 1.",
                    reason=WorldStateCorruptionReason.UNSUPPORTED_SCHEMA,
                )

            if "trucks" in raw_dict:
                raise WorldStateCorruptionError(
                    "Schema v1 world state payloads do not support truck snapshots.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )

            if not present_legacy_sections:
                raise WorldStateCorruptionError(
                    "World state payload must contain 'world' or complete legacy sections.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )

            missing_sections = [section for section in legacy_sections if section not in raw_dict]
            if missing_sections:
                missing = ", ".join(missing_sections)
                raise WorldStateCorruptionError(
                    f"Legacy world state payload is missing required section(s): {missing}.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )

            world_dict = {
                "counters": raw_dict["counters"],
                "customers": raw_dict["customers"],
                "packages": raw_dict["packages"],
                "routes": raw_dict["routes"],
                "trucks": raw_dict.get("trucks", []),
            }
        else:
            try:
                world_dict = self._require_mapping(world_obj)
            except TypeError as exc:
                raise WorldStateCorruptionError(
                    str(exc), reason=WorldStateCorruptionReason.INVALID_STRUCTURE
                ) from exc

            if schema_version == 1 and "trucks" in world_dict:
                raise WorldStateCorruptionError(
                    "Schema v1 world state payloads do not support truck snapshots.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )
            if schema_version == 2 and "trucks" not in world_dict:
                raise WorldStateCorruptionError(
                    "Schema v2 world state payloads require truck snapshots.",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                )
        try:
            counters_raw = self._require_mapping(world_dict.get("counters"))
            customers_raw = self._require_list(world_dict.get("customers"))
            packages_raw = self._require_list(world_dict.get("packages"))
            routes_raw = self._require_list(world_dict.get("routes"))
            trucks_raw = self._require_list(world_dict.get("trucks", []))
        except TypeError as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVALID_STRUCTURE
            ) from exc

        try:
            return WorldStateSnapshot(
                schema_version=schema_version,
                world=WorldSnapshotData(
                    counters=CountersSnapshot(
                        next_customer_id=self._require_int(counters_raw, "next_customer_id"),
                        next_package_id=self._require_int(counters_raw, "next_package_id"),
                        next_route_id=self._require_int(counters_raw, "next_route_id"),
                    ),
                    customers=tuple(self._customer_snapshot_from_raw(obj) for obj in customers_raw),
                    packages=tuple(self._package_snapshot_from_raw(obj) for obj in packages_raw),
                    routes=tuple(self._route_snapshot_from_raw(obj) for obj in routes_raw),
                    trucks=tuple(self._truck_snapshot_from_raw(obj) for obj in trucks_raw),
                ),
                users=None,
            )
        except TypeError as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVALID_STRUCTURE
            ) from exc
        except ValueError as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            ) from exc

    def _customer_snapshot_from_raw(self, raw: object) -> CustomerSnapshot:
        data = self._require_mapping(raw)
        return CustomerSnapshot(
            customer_id=self._require_int(data, "customer_id"),
            name=self._require_str(data, "name"),
            email=self._require_str(data, "email"),
            phone=self._require_str(data, "phone"),
        )

    def _package_snapshot_from_raw(self, raw: object) -> PackageSnapshot:
        data = self._require_mapping(raw)

        weight = require_positive_finite_float(data.get("weight"), "weight")
        route_id_raw = require_optional_int(data.get("route_id"), "route_id")

        return PackageSnapshot(
            package_id=self._require_int(data, "package_id"),
            start=LocationCode(self._require_str(data, "start")),
            end=LocationCode(self._require_str(data, "end")),
            weight=weight,
            customer_id=self._require_int(data, "customer_id"),
            route_id=route_id_raw,
        )

    def _route_snapshot_from_raw(self, raw: object) -> RouteSnapshot:
        data = self._require_mapping(raw)

        locations_raw = self._require_list(data.get("locations"))
        package_ids_raw = self._require_list(data.get("package_ids"))

        locations = [LocationCode(require_str(item, "route_location")) for item in locations_raw]

        package_ids = [require_int(item, "package_id") for item in package_ids_raw]

        truck_vehicle_id_raw = require_optional_int(
            data.get("truck_vehicle_id"),
            "truck_vehicle_id",
        )

        return RouteSnapshot(
            route_id=self._require_int(data, "route_id"),
            locations=tuple(locations),
            departure_time=self._require_str_or_none(data, "departure_time"),
            truck_vehicle_id=truck_vehicle_id_raw,
            package_ids=tuple(package_ids),
        )

    def _truck_snapshot_from_raw(self, raw: object) -> TruckSnapshot:
        data = self._require_mapping(raw)

        route_id_raw = require_optional_int(data.get("route_id"), "route_id")

        return TruckSnapshot(
            vehicle_id=self._require_int(data, "vehicle_id"),
            status=TruckStatus(self._require_str(data, "status")),
            current_location=self._require_location_or_none(data, "current_location"),
            route_id=route_id_raw,
            busy_from=self._require_str_or_none(data, "busy_from"),
            busy_until=self._require_str_or_none(data, "busy_until"),
            in_transit_to=self._require_location_or_none(data, "in_transit_to"),
        )

    def _require_mapping(self, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            raise TypeError("expected object")

        raw = cast(dict[object, object], value)
        result: dict[str, object] = {}

        for key, item in raw.items():
            if not isinstance(key, str):
                raise TypeError("object keys must be strings")
            result[key] = item

        return result

    def _require_list(self, value: object) -> list[object]:
        if not isinstance(value, list):
            raise TypeError("expected list")
        return cast(list[object], value)

    def _require_int(self, raw: dict[str, object], field: str) -> int:
        return require_int(raw.get(field), field)

    def _require_str(self, raw: dict[str, object], field: str) -> str:
        return require_str(raw.get(field), field)

    def _require_str_or_none(self, raw: dict[str, object], field: str) -> str | None:
        return require_optional_str(raw.get(field), field)

    def _require_location_or_none(self, raw: dict[str, object], field: str) -> LocationCode | None:
        value = self._require_str_or_none(raw, field)
        if value is None:
            return None
        return LocationCode(value)
