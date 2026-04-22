import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from src.domain.services.vehicle_manager import VehicleManager


class VehicleManager_Should(unittest.TestCase):
    @patch("src.domain.services.vehicle_manager.Map.get_locations", return_value=["L1", "L2", "L3"])
    def test_init_builds_fleet_and_disperses_round_robin(self, _get_locs: Any) -> None:
        vm = VehicleManager()
        # Fleet sizes per constructor: 10 + 15 + 15 = 40
        self.assertEqual(len(vm.vehicles), 40)

        # Deterministic round-robin by type across L1,L2,L3
        # First round across types: Scania(1001)->L1, Man(1011)->L2, Actros(1026)->L3
        first = {t.vehicle_id: t for t in vm.vehicles}
        self.assertEqual(first[1001].current_location, "L1")
        self.assertEqual(first[1011].current_location, "L2")
        self.assertEqual(first[1026].current_location, "L3")
        # Second round across types: Scania(1002)->L1, Man(1012)->L2, Actros(1027)->L3
        self.assertEqual(first[1002].current_location, "L1")
        self.assertEqual(first[1012].current_location, "L2")
        self.assertEqual(first[1027].current_location, "L3")

        # All trucks have one of the known locations
        self.assertTrue(all(t.current_location in {"L1", "L2", "L3"} for t in vm.vehicles))

    @patch("src.domain.services.vehicle_manager.Map.get_locations", return_value=["A", "B"])
    def test_list_fleet_returns_copy_and_find_by_id(self, _get_locs: Any) -> None:
        vm = VehicleManager()
        fleet1 = vm.list_fleet()
        fleet1.pop()  # mutate the returned list
        self.assertEqual(len(vm.vehicles), 40)  # internal list unchanged
        # find_by_id works for present and missing
        any_id = vm.vehicles[0].vehicle_id
        self.assertIs(vm.find_by_id(any_id), vm.vehicles[0])
        self.assertIsNone(vm.find_by_id(999999))

    # ---- is_suitable_for_route branches ----

    def _fake_route(
        self,
        *,
        total_distance: int,
        assigned_weight: float,
        start_loc: str,
        departure_time: datetime | None = None,
        truck_eta_final: datetime | None = None,
    ) -> tuple[SimpleNamespace, SimpleNamespace]:
        # total_assigned_weight is a callable; total_distance_km is an attribute (per implementation)
        r = SimpleNamespace(
            total_distance_km=total_distance,
            start_location=start_loc,
            departure_time=departure_time,
            eta_final=None,  # not used directly; truck.route.eta_final is used
        )

        def taw() -> float:
            return assigned_weight

        r.total_assigned_weight = taw
        # A "current" route the truck may already be on (with its eta_final)
        active_route = SimpleNamespace(eta_final=truck_eta_final)
        return r, active_route

    def _fake_truck(
        self,
        *,
        capacity: int,
        max_range: int,
        current_location: str,
        assigned_route: SimpleNamespace | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            capacity=capacity,
            max_range=max_range,
            current_location=current_location,
            route=assigned_route,
        )

    def test_is_suitable_false_range_too_short(self) -> None:
        vm = VehicleManager()
        r, _ = self._fake_route(total_distance=1000, assigned_weight=0, start_loc="SYD")
        t = self._fake_truck(capacity=1000, max_range=900, current_location="SYD")
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertFalse(ok)
        self.assertIn("range too short", reason)

    def test_is_suitable_false_insufficient_capacity(self) -> None:
        vm = VehicleManager()
        r, _ = self._fake_route(total_distance=100, assigned_weight=2000, start_loc="SYD")
        t = self._fake_truck(capacity=1500, max_range=1000, current_location="SYD")
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertFalse(ok)
        self.assertIn("insufficient capacity", reason)

    def test_is_suitable_false_wrong_location(self) -> None:
        vm = VehicleManager()
        r, _ = self._fake_route(total_distance=100, assigned_weight=0, start_loc="MEL")
        t = self._fake_truck(capacity=5000, max_range=5000, current_location="SYD")
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertFalse(ok)
        self.assertIn("wrong location", reason)
        self.assertIn("SYD", reason)
        self.assertIn("MEL", reason)

    def test_is_suitable_false_truck_busy_in_window(self) -> None:
        vm = VehicleManager()
        dep = datetime(2025, 1, 1, 10, 0)
        # Active route ends at 11:00 >= desired departure => busy
        r, active = self._fake_route(
            total_distance=100,
            assigned_weight=0,
            start_loc="SYD",
            departure_time=dep,
            truck_eta_final=datetime(2025, 1, 1, 11, 0),
        )
        t = self._fake_truck(capacity=1000, max_range=1000, current_location="SYD", assigned_route=active)
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertFalse(ok)
        self.assertIn("busy", reason)

    def test_is_suitable_false_route_not_scheduled_yet(self) -> None:
        vm = VehicleManager()
        # New route has no departure_time; truck already on some route -> reject
        r, active = self._fake_route(
            total_distance=100,
            assigned_weight=0,
            start_loc="SYD",
            departure_time=None,
            truck_eta_final=datetime(2025, 1, 1, 9, 0),
        )
        t = self._fake_truck(capacity=1000, max_range=1000, current_location="SYD", assigned_route=active)
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertFalse(ok)
        self.assertIn("route not scheduled yet", reason)

    def test_is_suitable_false_when_truck_already_assigned_with_unknown_availability(self) -> None:
        vm = VehicleManager()
        dep = datetime(2025, 1, 1, 10, 0)
        r, _active = self._fake_route(
            total_distance=100,
            assigned_weight=0,
            start_loc="SYD",
            departure_time=dep,
            truck_eta_final=None,
        )
        active = SimpleNamespace(eta_final=None)
        t = self._fake_truck(capacity=1000, max_range=1000, current_location="SYD", assigned_route=active)

        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]

        self.assertFalse(ok)
        self.assertIn("unknown availability", reason)

    def test_is_suitable_true_when_existing_assignment_ends_before_departure(self) -> None:
        vm = VehicleManager()
        dep = datetime(2025, 1, 1, 10, 0)
        r, active = self._fake_route(
            total_distance=100,
            assigned_weight=900,
            start_loc="SYD",
            departure_time=dep,
            truck_eta_final=datetime(2025, 1, 1, 9, 0),
        )
        t = self._fake_truck(capacity=1000, max_range=1000, current_location="SYD", assigned_route=active)

        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]

        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_is_suitable_true_when_all_conditions_ok(self) -> None:
        vm = VehicleManager()
        dep = datetime(2025, 1, 1, 10, 0)
        # Truck free (no assigned route), enough range/capacity, correct location
        r, _ = self._fake_route(
            total_distance=100, assigned_weight=900, start_loc="SYD", departure_time=dep, truck_eta_final=None
        )
        t = self._fake_truck(capacity=1000, max_range=1000, current_location="SYD", assigned_route=None)
        ok, reason = vm.is_suitable_for_route(t, r)  # type: ignore[reportArgumentType]
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    # ---- find_available_for_route ----

    def test_find_available_for_route_filters_and_sorts(self) -> None:
        vm = VehicleManager()
        # Replace vehicles with a small, controlled set
        vm.vehicles = [  # type: ignore[reportAttributeAccessIssue]
            SimpleNamespace(vehicle_id=5),
            SimpleNamespace(vehicle_id=2),
            SimpleNamespace(vehicle_id=9),
        ]
        # Allow only vehicle_ids {2, 9}
        allow = {2, 9}
        with patch.object(
            VehicleManager,
            "is_suitable_for_route",
            side_effect=lambda t, route: (t.vehicle_id in allow, ""),  # type: ignore[reportUnknownLambdaType, reportUnknownMemberType]
        ):
            res = vm.find_available_for_route(route=SimpleNamespace())  # type: ignore[reportArgumentType]
        # Sorted by vehicle_id
        ids = [t.vehicle_id for t in res]
        self.assertEqual(ids, [2, 9])
