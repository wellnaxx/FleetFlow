"""Validation for snapshot ids and repository counter bounds."""

from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldSnapshotData
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError


class IdentitySnapshotValidator:
    """Validate entity identity and counter invariants in a world snapshot."""

    def validate_counters(self, counters: CountersSnapshot) -> None:
        """Ensure snapshot counters are positive integers.

        Args:
            counters: Persisted repository counters.

        Raises:
            WorldStateCorruptionError: If any next-id counter is invalid.
        """
        if counters.next_customer_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_customer_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )

        if counters.next_package_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_package_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )
        if counters.next_route_id < 1:
            raise WorldStateCorruptionError(
                "Invalid next_route_id in snapshot.", reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            )

    def validate_ids(self, world: WorldSnapshotData) -> None:
        """Ensure entity and route package ids are positive and unique.

        Args:
            world: Snapshot payload containing customers, packages, and routes.

        Raises:
            WorldStateCorruptionError: If ids are invalid, duplicated, or a route
                has too few locations.
        """
        self._ensure_unique_ids(
            [customer.customer_id for customer in world.customers],
            "customer",
        )
        self._ensure_unique_ids(
            [package.package_id for package in world.packages],
            "package",
        )
        self._ensure_unique_ids(
            [route.route_id for route in world.routes],
            "route",
        )

        for route in world.routes:
            if len(route.locations) < 2:
                raise WorldStateCorruptionError(
                    f"Route {route.route_id} must contain at least two locations.",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            self._ensure_unique_ids(route.package_ids, f"package ids for route {route.route_id}")

    def _ensure_unique_ids(self, ids: tuple[int, ...] | list[int], label: str) -> None:
        seen: set[int] = set()
        duplicates: set[int] = set()

        for item_id in ids:
            if item_id < 1:
                raise WorldStateCorruptionError(
                    f"Invalid {label} id in snapshot: {item_id}",
                    reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
                )
            if item_id in seen:
                duplicates.add(item_id)
            seen.add(item_id)

        if duplicates:
            dupes = ", ".join(str(item_id) for item_id in sorted(duplicates))
            raise WorldStateCorruptionError(
                f"Duplicate {label} ids in snapshot: {dupes}",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )

    def validate_counter_bounds(self, world: WorldSnapshotData) -> None:
        """Ensure next-id counters are greater than existing entity ids.

        Args:
            world: Snapshot payload with counters and entity collections.

        Raises:
            WorldStateCorruptionError: If a counter would reuse an existing id.
        """
        self._validate_next_id(
            label="customer",
            next_id=world.counters.next_customer_id,
            existing_ids=[customer.customer_id for customer in world.customers],
        )
        self._validate_next_id(
            label="package",
            next_id=world.counters.next_package_id,
            existing_ids=[package.package_id for package in world.packages],
        )
        self._validate_next_id(
            label="route",
            next_id=world.counters.next_route_id,
            existing_ids=[route.route_id for route in world.routes],
        )

    def _validate_next_id(self, *, label: str, next_id: int, existing_ids: list[int]) -> None:
        if existing_ids and next_id <= max(existing_ids):
            raise WorldStateCorruptionError(
                f"Invalid next_{label}_id in snapshot: {next_id} must be greater than existing {label} ids.",
                reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
            )
