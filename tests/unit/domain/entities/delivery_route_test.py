import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.domain.entities.delivery_route import DeliveryRoute

LOCATIONS = ["A", "B", "C", "D"]
# distances between consecutive pairs (A->B, B->C, C->D)
DIST = {("A", "B"): 100, ("B", "C"): 200, ("C", "D"): 300}


def get_dist(a: str, b: str) -> int:
    return DIST[(a, b)]


class _Pkg:
    def __init__(self, package_id: int, start: str, end: str, weight: float = 0.0) -> None:
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight
        self.route: DeliveryRoute | None = None
        self.expected_arrival: datetime | None = None


class _Truck:
    def __init__(
        self,
        vehicle_id: int = 1,
        capacity: int = 999999,
        max_range: int = 999999,
        current_location: str | None = None,
        route: DeliveryRoute | None = None,
    ) -> None:
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.max_range = max_range
        self.current_location = current_location
        self.route = route


@patch("src.domain.entities.delivery_route.Map.get_locations", return_value=LOCATIONS)
@patch("src.domain.entities.delivery_route.Map.get_distance", side_effect=get_dist)
class DeliveryRoute_Should(unittest.TestCase):
    def test_init_validates_locations_and_sets_id_or_uses_provided(self, *_):
        r = DeliveryRoute("A", "B", route_id=123)
        self.assertEqual(r.route_id, 123)
        self.assertEqual(r.start_location, "A")
        self.assertEqual(r.end_location, "B")
        with self.assertRaises(ValueError):
            DeliveryRoute("A", route_id=1)  # needs at least two
        with self.assertRaises(ValueError):
            DeliveryRoute("A", "Z", route_id=1)  # invalid code

    def test_init_rejects_duplicate_locations(self, *_):
        with self.assertRaises(ValueError) as ctx:
            DeliveryRoute("A", "B", "A", route_id=1)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_schedule_builds_segments_and_stop_times_eta_final(self, *_):
        base = datetime(2025, 1, 1, 8, 0, 0)
        r = DeliveryRoute("A", "B", "C", route_id=1)
        r.schedule(base)
        # A->B: 100 km, B->C: 200 km @ 87 km/h
        dur_ab = timedelta(hours=100 / DeliveryRoute.SPEED_KMPH)
        dur_bc = timedelta(hours=200 / DeliveryRoute.SPEED_KMPH)
        self.assertEqual(r.arrival_time_at("A"), base)
        self.assertEqual(r.arrival_time_at("B"), base + dur_ab)
        self.assertEqual(r.arrival_time_at("C"), base + dur_ab + dur_bc)
        self.assertEqual(r.eta_final, base + dur_ab + dur_bc)

    def test_total_distance_km_uses_map_sum_and_cached_segments(self, *_):
        r = DeliveryRoute("A", "B", "C", "D", route_id=1)
        # unscheduled path: uses Map.get_distance sum
        self.assertEqual(r.total_distance_km, 100 + 200 + 300)
        # scheduled path: uses precomputed segments (still same sum)
        r.schedule(datetime(2025, 1, 1, 9, 0))
        self.assertEqual(r.total_distance_km, 100 + 200 + 300)

    def test_arrival_time_at_validations(self, *_):
        r = DeliveryRoute("A", "B", "C", route_id=1)
        with self.assertRaises(ValueError):
            _ = r.arrival_time_at("A")  # unscheduled
        r.schedule(datetime(2025, 1, 1, 9, 0))
        with self.assertRaises(ValueError):
            _ = r.arrival_time_at("D")  # not on route

    def test_current_position_all_cases(self, *_):
        base = datetime(2025, 1, 1, 8, 0)
        r = DeliveryRoute("A", "B", "C", route_id=1)
        r.schedule(base)

        # UNSCHEDULED: separate route
        r_uns = DeliveryRoute("A", "B", route_id=2)
        pos_u = r_uns.current_position(base)
        self.assertEqual(pos_u.kind, "UNSCHEDULED")
        self.assertEqual(pos_u.stop_city, "A")

        # BEFORE_START
        t0 = base - timedelta(minutes=5)
        pos0 = r.current_position(t0)
        self.assertEqual(pos0.kind, "BEFORE_START")
        self.assertEqual(pos0.stop_city, "A")
        self.assertIsInstance(pos0.next_eta, datetime)

        # Exactly at A arrival => IN_TRANSIT for first leg per code’s rule
        tA = r.arrival_time_at("A")
        posA = r.current_position(tA)
        self.assertEqual(posA.kind, "IN_TRANSIT")
        self.assertEqual(posA.from_city, "A")
        self.assertEqual(posA.to_city, "B")

        # In transit A->B (strictly between)
        tAB_mid = tA + (r.arrival_time_at("B") - tA) / 2
        posAB = r.current_position(tAB_mid)
        self.assertEqual(posAB.kind, "IN_TRANSIT")
        self.assertEqual(posAB.from_city, "A")
        self.assertEqual(posAB.to_city, "B")

        # Exactly at B => AT_STOP
        tB = r.arrival_time_at("B")
        posB = r.current_position(tB)
        self.assertEqual(posB.kind, "AT_STOP")
        self.assertEqual(posB.stop_city, "B")

        # After final arrival => AFTER_END
        t_after = r.arrival_time_at("C") + timedelta(seconds=1)
        pos_end = r.current_position(t_after)
        self.assertEqual(pos_end.kind, "AFTER_END")
        self.assertEqual(pos_end.stop_city, "C")

    def test_includes_in_order(self, *_):
        r = DeliveryRoute("A", "B", "C", "D", route_id=1)
        self.assertTrue(r.includes_in_order("A", "D"))
        self.assertTrue(r.includes_in_order("B", "C"))
        self.assertFalse(r.includes_in_order("C", "B"))  # wrong order
        self.assertFalse(r.includes_in_order("A", "A"))  # not strictly increasing
        self.assertFalse(r.includes_in_order("A", "Z"))  # not present

    def test_can_accept_package_checks_inclusion_capacity_and_range(self, *_):
        base = datetime(2025, 1, 1, 7, 0)
        r = DeliveryRoute("A", "B", "C", "D", route_id=1)
        r.schedule(base)

        # Truck with limited capacity and range (total route distance: 600 km)
        r.truck = _Truck(vehicle_id=10, capacity=50, max_range=500, current_location="A")  # type: ignore[reportAttributeAccessIssue]

        # Inclusion failure
        p_bad = _Pkg(1, "A", "Z", 10)
        self.assertIn("does not include start/end", r.can_accept_package(p_bad))  # type: ignore[reportArgumentType]

        # Order failure
        p_order = _Pkg(2, "C", "B", 10)
        self.assertIn("does not pass from C to B in order", r.can_accept_package(p_order))  # type: ignore[reportArgumentType]

        # Capacity failure (current total 0 + 60 > 50)
        p_cap = _Pkg(3, "A", "B", 60)
        self.assertIn("capacity exceeded", r.can_accept_package(p_cap))  # type: ignore[reportArgumentType]

        # Range failure: make capacity ok but range short
        r.truck.capacity = 1000  # type: ignore[reportOptionalMemberAccess]
        self.assertIn("lacks range for 600 km", r.can_accept_package(_Pkg(4, "A", "C", 1)))  # type: ignore[reportArgumentType]

        # Success when both capacity and range ok
        r.truck.max_range = 1000  # type: ignore[reportOptionalMemberAccess]
        ok_err = r.can_accept_package(_Pkg(5, "A", "C", 10))  # type: ignore[reportArgumentType]
        self.assertIsNone(ok_err)

    def test_can_accept_package_allows_before_pickup_and_blocks_after_pickup(self, *_):
        base = datetime(2025, 1, 1, 8, 0)
        route = DeliveryRoute("A", "B", "C", route_id=1)
        route.schedule(base)

        start_pkg = _Pkg(1, "A", "C", 5)
        mid_pkg = _Pkg(2, "B", "C", 5)

        self.assertIsNone(route.can_accept_package(start_pkg, now=base - timedelta(seconds=1)))  # type: ignore[reportArgumentType]
        self.assertIn(
            "already passed pickup location A",
            route.can_accept_package(start_pkg, now=base),  # type: ignore[reportArgumentType]
        )

        stop_b = route.arrival_time_at("B")
        self.assertIsNone(route.can_accept_package(mid_pkg, now=stop_b))  # type: ignore[reportArgumentType]
        self.assertIn(
            "already passed pickup location B",
            route.can_accept_package(mid_pkg, now=stop_b + timedelta(seconds=1)),  # type: ignore[reportArgumentType]
        )

    def test_can_accept_package_unscheduled_route_ignores_pickup_passed_rule(self, *_):
        route = DeliveryRoute("A", "B", "C", route_id=1)
        package = _Pkg(1, "B", "C", 5)

        self.assertIsNone(route.can_accept_package(package, now=datetime(2025, 1, 1, 8, 0)))  # type: ignore[reportArgumentType]

    def test_assign_package_sets_links_and_expected_arrival_when_scheduled(self, *_):
        base = datetime(2025, 1, 1, 6, 0)
        r = DeliveryRoute("A", "B", "C", route_id=1)
        r.schedule(base)
        p = _Pkg(1, "A", "C", 5)

        r.assign_package(p)  # type: ignore[reportArgumentType]
        self.assertIs(p.route, r)
        self.assertIn(p, r.packages)
        self.assertIsInstance(p.expected_arrival, datetime)
        # assigning the same package twice should be a no-op (no duplicate)
        r.assign_package(p)  # type: ignore[reportArgumentType]
        self.assertEqual(len(r.packages), 1)

    def test_assign_package_unscheduled_sets_no_eta(self, *_):
        r = DeliveryRoute("A", "B", route_id=1)
        p = _Pkg(1, "A", "B", 1)
        r.assign_package(p)  # type: ignore[reportArgumentType]
        self.assertIs(p.route, r)
        self.assertIsNone(p.expected_arrival)

    def test_detach_package_removes_package_and_clears_backref(self, *_):
        r = DeliveryRoute("A", "B", "C", route_id=1)
        p = _Pkg(1, "A", "C", 5)

        r.assign_package(p)  # type: ignore[reportArgumentType]
        self.assertIs(p.route, r)
        self.assertIn(p, r.packages)

        r.detach_package(p)  # type: ignore[reportArgumentType]

        self.assertIsNone(p.route)
        self.assertNotIn(p, r.packages)

    def test_detach_package_only_removes_target(self, *_):
        r = DeliveryRoute("A", "B", "C", route_id=1)
        p1 = _Pkg(1, "A", "B", 5)
        p2 = _Pkg(2, "A", "C", 7)

        r.assign_package(p1)  # type: ignore[reportArgumentType]
        r.assign_package(p2)  # type: ignore[reportArgumentType]

        r.detach_package(p1)  # type: ignore[reportArgumentType]

        self.assertIsNone(p1.route)
        self.assertNotIn(p1, r.packages)

        self.assertIs(p2.route, r)
        self.assertIn(p2, r.packages)
        self.assertEqual(len(r.packages), 1)

    def test_detach_package_raises_when_not_assigned(self, *_):
        r = DeliveryRoute("A", "B", "C", route_id=1)
        p = _Pkg(1, "A", "C", 5)

        with self.assertRaises(ValueError) as ctx:
            r.detach_package(p)  # type: ignore[reportArgumentType]

        self.assertIn("1", str(ctx.exception))
        self.assertNotIn(p, r.packages)
        self.assertIsNone(p.route)

    def test_detach_package_raises_when_assigned_to_different_route(self, *_):
        r1 = DeliveryRoute("A", "B", "C", route_id=1)
        r2 = DeliveryRoute("A", "B", "C", route_id=2)
        p = _Pkg(1, "A", "C", 5)

        r2.assign_package(p)  # type: ignore[reportArgumentType]

        with self.assertRaises(ValueError) as ctx:
            r1.detach_package(p)  # type: ignore[reportArgumentType]

        self.assertIn("1", str(ctx.exception))
        self.assertIs(p.route, r2)
        self.assertIn(p, r2.packages)
        self.assertNotIn(p, r1.packages)

    def test_info_contains_key_lines(self, *_):
        base = datetime(2025, 1, 1, 8, 0)
        r = DeliveryRoute("A", "B", "C", route_id=1)
        r.schedule(base)
        info = r.info()
        # Must include route id, truck (none), start/end, departure,
        # distance, stops header, status/assigned weight
        self.assertIn(f"Route ID: {r.route_id}", info)
        self.assertIn("Truck ID: Not assigned", info)
        self.assertIn("Start: A", info)
        self.assertIn("End: C", info)
        self.assertIn("Departure:", info)
        self.assertIn("Total Distance: 300 km", info)
        self.assertIn("Stops:", info)
        self.assertIn("Assigned weight: 0.00 kg", info)
        # Status is one of BEFORE_START/AT_STOP/IN_TRANSIT/AFTER_END
        # (at schedule time it's AT_STOP or IN_TRANSIT per code)
        self.assertTrue(
            any(
                s in info
                for s in [
                    "Status: AT_STOP",
                    "Status: IN_TRANSIT",
                    "Status: BEFORE_START",
                    "Status: AFTER_END",
                ]
            )
        )
