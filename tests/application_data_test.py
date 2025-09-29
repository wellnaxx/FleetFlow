# application_data_test.py
import unittest
from unittest.mock import patch, MagicMock, mock_open
from types import SimpleNamespace
from datetime import datetime, timedelta
import json

from src.core.application_data import ApplicationData
from src.models.auth import Role
from src.models.item_status import ItemStatus


# --- Minimal fakes for ContactInfo & Customer used inside _find_or_create_customer ---

class _FakeContactInfo:
    def __init__(self, name, email, phone_number):
        self.name = name
        self.email = email
        self.phone_number = phone_number


class _FakeCustomer:
    def __init__(self, customer_id, contact: _FakeContactInfo):
        self.customer_id = customer_id
        # expose fields the code reads
        self.name = contact.name
        self.email = contact.email
        self.phone_number = contact.phone_number
        self._packages = []

    def add_package(self, p):
        self._packages.append(p)


def _mk_app():
    """ApplicationData with permissive authz and a stubbed vehicle manager."""
    app = ApplicationData(current_user=None)
    app.authz = SimpleNamespace(
        has=lambda *args, **kwargs: True,
        has_all=lambda *args, **kwargs: True,
    )
    app.vehicle_manager = MagicMock()
    app.vehicle_manager.vehicles = []
    return app


# ---------------------------
# Lightweight fakes for route/truck/pkg where helpful
# ---------------------------

class _FakeTruck:
    def __init__(self, vehicle_id=1, capacity=100.0, current_location="BASE"):
        self.vehicle_id = vehicle_id
        self.capacity = capacity
        self.current_location = current_location
        self.in_transit_to = None
        self.route = None

    def assign(self, route, start_loc):
        self.route = route
        self.current_location = start_loc
        return True

    def release(self, now=None, force=False):
        released = self.route is not None
        self.route = None
        self.in_transit_to = None
        return released


class _FakeRoute:
    def __init__(self, route_id, locations, departure_time=None, eta_final=None):
        self.route_id = route_id
        self.locations = list(locations)
        self.start_location = locations[0]
        self.end_location = locations[-1]
        self.departure_time = departure_time
        self.eta_final = eta_final
        self.truck = None
        self.packages = []

    def schedule(self, when):
        self.departure_time = when

    def total_assigned_weight(self):
        return sum(getattr(p, "weight", 0.0) for p in self.packages)

    def assign_package(self, pkg):
        self.packages.append(pkg)
        pkg.route = self

    def arrival_time_at(self, city):
        idx = self.locations.index(city)
        if self.departure_time is None:
            raise ValueError("unscheduled")
        return self.departure_time + timedelta(hours=idx)

    def current_position(self, now):
        if self.departure_time is None:
            return SimpleNamespace(kind="UNSCHEDULED")
        if now < self.departure_time:
            return SimpleNamespace(kind="BEFORE_START")
        if self.eta_final and now >= self.eta_final:
            return SimpleNamespace(kind="AFTER_END")
        for i, city in enumerate(self.locations):
            t = self.arrival_time_at(city)
            if abs((now - t).total_seconds()) < 1e-6:
                return SimpleNamespace(kind="AT_STOP", stop_city=city)
            if now < t:
                prev = self.locations[i - 1] if i > 0 else self.start_location
                return SimpleNamespace(kind="IN_TRANSIT", from_city=prev, to_city=city, next_eta=self.arrival_time_at(city))
        return SimpleNamespace(kind="AT_STOP", stop_city=self.end_location)


class _FakePackage:
    def __init__(self, package_id, start, end, weight=1.0, customer=None):
        self.package_id = package_id
        self.start_location = start
        self.end_location = end
        self.weight = weight
        self.customer = customer or SimpleNamespace(customer_id=1)
        self.route = None
        self.status = None


# ---------------------------
# Tests
# ---------------------------

class ApplicationData_CustomerFinding_Should(unittest.TestCase):
    @patch('src.core.application_data.Customer', _FakeCustomer)
    @patch('src.core.application_data.ContactInfo', _FakeContactInfo)
    def test_same_name_and_find_or_create_new_customer(self):
        app = _mk_app()

        # same_name behavior (case/whitespace insensitive)
        self.assertTrue(app._same_name("  Alice  ", "alice"))
        self.assertFalse(app._same_name("Alice", "Alicia"))

        # Creates a new customer and indexes by email/phone
        c = app._find_or_create_customer(" Alice  ", "ALICE@EX.COM ", " 0412 345 678 ")
        self.assertEqual(c.name, "Alice")
        self.assertEqual(c.email, "alice@ex.com")
        self.assertEqual(c.phone_number, "0412345678")
        # Indexed
        self.assertIs(app._customers_by_email["alice@ex.com"], c)
        self.assertIs(app._customers_by_phone["0412345678"], c)
        # Returned in .customers
        self.assertIn(c, app.customers)

    @patch('src.core.application_data.Customer', _FakeCustomer)
    @patch('src.core.application_data.ContactInfo', _FakeContactInfo)
    def test_find_or_create_reuses_by_email_and_validates_name(self):
        app = _mk_app()
        # seed one
        c1 = app._find_or_create_customer("Bob", "bob@ex.com", "")
        # same email, matching name (case-insensitive) => reuse
        c_again = app._find_or_create_customer("  bob  ", "BOB@EX.COM", "")
        self.assertIs(c_again, c1)

        # mismatching name with same email => error
        with self.assertRaises(ValueError):
            app._find_or_create_customer("Bobby", "bob@ex.com", "")

    @patch('src.core.application_data.Customer', _FakeCustomer)
    @patch('src.core.application_data.ContactInfo', _FakeContactInfo)
    def test_find_or_create_reuses_by_phone_and_validates_name(self):
        app = _mk_app()
        c1 = app._find_or_create_customer("Carol", "", "04 11 22 33 44")
        # reuse by phone
        c_again = app._find_or_create_customer("carol", "", "0411223344")
        self.assertIs(c_again, c1)

        # mismatching name with same phone => error
        with self.assertRaises(ValueError):
            app._find_or_create_customer("Different", "", "0411223344")

    @patch('src.core.application_data.Customer', _FakeCustomer)
    @patch('src.core.application_data.ContactInfo', _FakeContactInfo)
    def test_find_or_create_conflict_email_and_phone_different_customers(self):
        app = _mk_app()
        _ = app._find_or_create_customer("Dan", "dan@ex.com", "")
        _ = app._find_or_create_customer("Dan", "", "0400000000")
        with self.assertRaises(ValueError):
            app._find_or_create_customer("Dan", "dan@ex.com", "0400000000")

    @patch('src.core.application_data.Customer', _FakeCustomer)
    @patch('src.core.application_data.ContactInfo', _FakeContactInfo)
    def test_find_or_create_name_only_reuse_when_unambiguous(self):
        app = _mk_app()
        c_alice = app._find_or_create_customer("Alice", "", "")
        _ = app._find_or_create_customer("Bob", "bob@ex.com", "")
        c_again = app._find_or_create_customer("alice", "", "")
        self.assertIs(c_again, c_alice)


class ApplicationData_CreateRemove_Should(unittest.TestCase):
    @patch('src.core.application_data.Map.is_valid_location', return_value=True)
    def test_create_route_find_and_remove(self, _is_valid):
        app = _mk_app()
        # Patch DeliveryRoute to bypass its own strict validation
        with patch('src.core.application_data.DeliveryRoute') as DR:
            # make a simple route object exposing attributes used later
            DR.side_effect = lambda *locs, departure_time=None, route_id=None: SimpleNamespace(
                route_id=route_id,
                locations=list(locs),
                start_location=locs[0],
                end_location=locs[-1],
                departure_time=departure_time,
                packages=[],
                truck=None,
            )
            r = app.create_route(["A", "B"], None)
            self.assertIs(app.find_route(r.route_id), r)
            # attach truck and ensure release on remove
            truck = _FakeTruck(vehicle_id=5)
            r.truck = truck
            truck.route = r
            removed = app.remove_route(r.route_id)
            self.assertIs(removed, r)
            self.assertIsNone(truck.route)

    @patch('src.core.application_data.Map.is_valid_location', side_effect=lambda c: c != "BAD")
    def test_create_route_validates_locations(self, is_valid):
        app = _mk_app()
        with self.assertRaises(ValueError):
            app.create_route(["A"], None)

        with self.assertRaises(ValueError):
            app.create_route(["A", "BAD"], None)

        # Patch DeliveryRoute so the “happy path” doesn’t hit real validation
        with patch('src.core.application_data.DeliveryRoute') as DR:
            DR.side_effect = lambda *locs, departure_time=None, route_id=None: SimpleNamespace(
                route_id=route_id,
                locations=list(locs),
                start_location=locs[0],
                end_location=locs[-1],
                departure_time=departure_time,
                packages=[],
                truck=None,
            )
            _ = app.create_route(["A", "B", "C"], None)  # ok under our Map + fake DeliveryRoute


    def test_create_package_and_remove(self):
        with patch('src.core.application_data.ContactInfo', autospec=True) as CI, \
            patch('src.core.application_data.Customer', autospec=True) as Cust, \
            patch('src.core.application_data.DeliveryPackage') as DP:
            # minimal Customer stub the code expects
            def mk_customer(customer_id, contact):
                return SimpleNamespace(
                    customer_id=customer_id,
                    name=getattr(contact, "name", "X"),
                    email=getattr(contact, "email", ""),
                    phone_number=getattr(contact, "phone_number", ""),
                    add_package=lambda p: None
                )
            Cust.side_effect = mk_customer

            # minimal DeliveryPackage stub bypassing real validation
            DP.side_effect = lambda start, end, weight, customer, package_id=None: SimpleNamespace(
                package_id=package_id,
                start_location=start,
                end_location=end,
                weight=weight,
                customer=customer,
                route=None,
            )

            app = _mk_app()
            p = app.create_package("S", "E", 3.5, "N", "e@x.com", "0412")
            self.assertEqual(len(app.packages), 1)

            # remove non-existent -> error
            with self.assertRaises(ValueError):
                app.remove_package(999)

            # remove existing
            removed = app.remove_package(p.package_id)
            self.assertEqual(removed.package_id, p.package_id)
            self.assertEqual(len(app.packages), 0)

    def test_view_routes_and_packages_helpers(self):
        app = _mk_app()
        r = SimpleNamespace(route_id=1)
        p = SimpleNamespace(package_id=2)
        app._routes = [r]
        app._packages = [p]
        self.assertIn(r, app.routes)
        self.assertIn(p, app.packages)
        self.assertIn(r, app.view_all_routes())
        self.assertIn(p, app.view_all_packages())


class ApplicationData_AssignPackages_Should(unittest.TestCase):
    def _seed_app_with_route_and_packages(self, scheduled=False):
        app = _mk_app()
        route = SimpleNamespace(
            route_id=10,
            start_location="SYD",
            end_location="MEL",
            locations=["SYD", "CBR", "MEL"],
            packages=[],
            truck=None,
            departure_time=(datetime(2025, 10, 1, 9, 0) if scheduled else None),
        )

        def arrival_time_at(city):
            table = {"SYD": datetime(2025, 10, 1, 9, 0), "CBR": datetime(2025, 10, 1, 12, 0), "MEL": datetime(2025, 10, 1, 18, 0)}
            return table.get(city)
        route.arrival_time_at = arrival_time_at
        app._routes.append(route)

        pkg1 = SimpleNamespace(package_id=1, end_location="MEL", route=None)
        pkg2 = SimpleNamespace(package_id=2, end_location="CBR", route=None)
        pkg3 = SimpleNamespace(package_id=3, end_location="MEL", route=route)
        app._packages.extend([pkg1, pkg2, pkg3])
        return app, route, (pkg1, pkg2, pkg3)

    def test_assign_packages_unscheduled_route_formats_eta_na(self):
        app, route, (pkg1, _, _) = self._seed_app_with_route_and_packages(scheduled=False)
        out_parts = app.assign_packages_to_route(route.route_id, [pkg1.package_id])
        self.assertEqual(
            out_parts,
            [f"Assigned package {pkg1.package_id} to route {route.route_id}. ETA: N/A (route unscheduled)"],
        )
        self.assertIs(pkg1.route, route)
        self.assertIn(pkg1, route.packages)

    def test_assign_packages_scheduled_mixes_success_and_errors(self):
        app, route, (pkg1, _, pkg3) = self._seed_app_with_route_and_packages(scheduled=True)
        out = app.assign_packages_to_route(route.route_id, [pkg1.package_id, 99, pkg3.package_id, pkg1.package_id])
        txt = "\n".join(out)
        self.assertIn("Assigned package 1 to route 10. ETA: 2025-10-01 18:00", txt)
        self.assertIn("Failed:", txt)
        self.assertIn("Package 99 not found.", txt)
        self.assertIn("already on route 10", txt)

    def test_assign_packages_all_errors_raise(self):
        app, route, (_, _, pkg3) = self._seed_app_with_route_and_packages(scheduled=True)
        app._packages = [pkg3]
        with self.assertRaises(ValueError) as ctx:
            app.assign_packages_to_route(route.route_id, [999, pkg3.package_id])
        self.assertIn("No packages could be assigned:", str(ctx.exception))


class ApplicationData_FindSuitables_Should(unittest.TestCase):
    def test_find_suitable_routes_for_package_capacity_and_sort(self):
        app = _mk_app()
        r1 = _FakeRoute(10, ["A", "B", "C"], departure_time=datetime(2025,1,1,8), eta_final=datetime(2025,1,1,10))
        r2 = _FakeRoute(20, ["A", "X", "C"], departure_time=datetime(2025,1,1,9), eta_final=datetime(2025,1,1,11))
        r3 = _FakeRoute(30, ["A", "C"])  # unscheduled
        t1 = _FakeTruck(vehicle_id=100, capacity=5.0)
        t2 = _FakeTruck(vehicle_id=200, capacity=1.0)  # too small
        r1.truck = t1
        r2.truck = t2

        app._routes = [r3, r2, r1]
        cust = SimpleNamespace(customer_id=1)
        pkg = _FakePackage(7, "A", "C", weight=2.0, customer=cust)
        app._packages = [pkg]

        res = app.find_suitable_routes_for_package(pkg.package_id)
        ids = [x["route"].route_id for x in res]
        self.assertEqual(ids, [10, 30])

    def test_find_suitable_trucks_for_route_delegates(self):
        app = _mk_app()
        r = _FakeRoute(9, ["A", "B"])
        app._routes = [r]
        app.vehicle_manager.find_available_for_route.return_value = ["T1", "T2"]
        out = app.find_suitable_trucks_for_route(9)
        self.assertEqual(out, ["T1", "T2"])
        app.vehicle_manager.find_available_for_route.assert_called_once()


class ApplicationData_AssignTruckAndHeartbeat_Should(unittest.TestCase):
    def test_assign_truck_schedules_if_unscheduled_and_checks_suitability(self):
        app = _mk_app()
        r = _FakeRoute(1, ["S", "E"])  # unscheduled initially
        app._routes = [r]
        truck = _FakeTruck(vehicle_id=5, capacity=10.0)
        app.vehicle_manager.find_by_id.return_value = truck
        app.vehicle_manager.is_suitable_for_route.return_value = (True, "")

        result = app.assign_truck_to_route(5, 1)
        self.assertIs(result, r)
        self.assertIs(r.truck, truck)
        self.assertIs(truck.route, r)
        self.assertIsNotNone(r.departure_time)

    def test_assign_truck_not_found_errors(self):
        app = _mk_app()
        r = _FakeRoute(1, ["S", "E"])
        app._routes = [r]
        app.vehicle_manager.find_by_id.return_value = None
        with self.assertRaises(ValueError):
            app.assign_truck_to_route(99, 1)

    def test_heartbeat_moves_trucks_and_updates_packages(self):
        app = _mk_app()
        base = datetime(2025, 1, 1, 8, 0)

        # BEFORE_START
        r1 = _FakeRoute(1, ["S1", "E1"], departure_time=base + timedelta(hours=2), eta_final=base + timedelta(hours=3))
        t1 = _FakeTruck(vehicle_id=1); r1.truck = t1; t1.route = r1; t1.current_location = "X"
        # AT_STOP then AFTER_END
        r2 = _FakeRoute(2, ["S2", "E2"], departure_time=base, eta_final=base + timedelta(hours=1))
        t2 = _FakeTruck(vehicle_id=2); r2.truck = t2; t2.route = r2
        # IN_TRANSIT
        r3 = _FakeRoute(3, ["S3", "M3", "E3"], departure_time=base, eta_final=base + timedelta(hours=2))
        t3 = _FakeTruck(vehicle_id=3); r3.truck = t3; t3.route = r3
        # UNSCHEDULED
        r4 = _FakeRoute(4, ["S4", "E4"], departure_time=None, eta_final=None)

        cust = SimpleNamespace(customer_id=1)
        p_a = _FakePackage(1, "S3", "M3", weight=1, customer=cust)
        p_b = _FakePackage(2, "S3", "E3", weight=1, customer=cust)
        r3.assign_package(p_a); r3.assign_package(p_b)

        app._routes = [r1, r2, r3, r4]
        app.vehicle_manager.vehicles = [t1, t2, t3]
        app._packages += [p_a, p_b]

        # 1) exactly departure for r2 -> AT_STOP
        summary1 = app.heartbeat(now=base)
        self.assertGreaterEqual(summary1["trucks_moved"], 0)

        # 2) IN_TRANSIT on r3 between S3->M3 (now S3->M3, should set in_transit_to and count a move)
        mid = base + timedelta(minutes=30)
        summary2 = app.heartbeat(now=mid)
        self.assertGreaterEqual(summary2["trucks_moved"], 1)
        self.assertEqual(p_a.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(p_b.status, ItemStatus.IN_PROGRESS)

        # 3) AFTER_END triggers release on r2
        summary3 = app.heartbeat(now=base + timedelta(hours=2))
        self.assertGreaterEqual(summary3["trucks_released"], 1)

        # route status helper sanity
        self.assertIn(app._compute_route_status(r4, base), {"PLANNED"})
        self.assertEqual(app._compute_route_status(r1, base + timedelta(hours=1)), "SCHEDULED")
        self.assertEqual(app._compute_route_status(r3, base + timedelta(hours=3)), "COMPLETED")



class ApplicationData_SaveLoad_Should(unittest.TestCase):
    @patch('src.core.application_data.resolve_data_path', return_value="C:/fake/state.json")
    @patch('src.core.application_data.os.path.exists', return_value=True)
    @patch('src.core.application_data.open', new_callable=mock_open)
    @patch('src.core.application_data.json.load')
    def test_load_reads_and_applies(self, mock_json_load, m_open, _exists, _resolve):
        app = _mk_app()
        payload = {
            "schema_version": 1,
            "counters": {"next_customer_id": 2, "next_package_id": 3, "next_route_id": 4},
            "customers": [{"customer_id": 1, "name": "Name", "email": "", "phone": ""}],
            "packages": [{"package_id": 1, "start": "SYD", "end": "MEL", "weight": 1.0, "customer_id": 1, "route_id": None}],
            "routes": [{"route_id": 10, "locations": ["SYD", "MEL"], "departure_time": None, "truck_vehicle_id": None, "package_ids": []}],
        }
        mock_json_load.return_value = payload

        with patch('src.core.application_data.ContactInfo') as CI, \
             patch('src.core.application_data.Customer') as Cust, \
             patch('src.core.application_data.DeliveryPackage') as DP, \
             patch('src.core.application_data.DeliveryRoute') as DR, \
             patch.object(app, 'heartbeat', return_value={}):
            cust_obj = SimpleNamespace(customer_id=1, name="Name", email="", phone_number="", add_package=lambda p: None)
            Cust.side_effect = lambda customer_id, contact: cust_obj
            CI.side_effect = lambda name, email, phone_number: SimpleNamespace(name=name, email=email, phone_number=phone_number)
            pkg_obj = SimpleNamespace(package_id=1, start_location="SYD", end_location="MEL", weight=1.0, customer=cust_obj)
            DP.side_effect = lambda *args, **kwargs: pkg_obj
            DR.side_effect = lambda *args, **kwargs: SimpleNamespace(route_id=10, locations=["SYD","MEL"], packages=[])

            msg = app.load("state.json")
            self.assertIn("Loaded state from", msg)
            self.assertTrue(app._customers)
            self.assertTrue(app._packages)
            self.assertTrue(app._routes)

    @patch('src.core.application_data.resolve_data_path', return_value="C:/fake/missing.json")
    @patch('src.core.application_data.os.path.exists', return_value=False)
    def test_load_missing_raises(self, _exists, _resolve):
        app = _mk_app()
        with self.assertRaises(ValueError):
            app.load("missing.json")

    @patch('src.core.application_data.resolve_data_path', return_value="C:/fake/state.json")
    @patch('src.core.application_data.tempfile.mkstemp', return_value=(123, "C:/fake/.appstate.tmp.json"))
    @patch('src.core.application_data.os.fdopen')
    @patch('src.core.application_data.os.replace')
    @patch('src.core.application_data.os.path.dirname', return_value="C:/fake")
    @patch('src.core.application_data.os.makedirs')
    def test_persist_to_file_writes_atomically(self, makedirs, dirname, replace, fdopen, mkstemp, resolve):
        app = _mk_app()
        with patch.object(app, "_dump_state", return_value={"ok": True}):
            cm = MagicMock()
            fdopen.return_value.__enter__.return_value = cm
            path = app._persist_to_file("state.json")
            self.assertEqual(path, "C:/fake/state.json")
            makedirs.assert_called_once()
            replace.assert_called_once()  # atomic rename

    def test_register_user_delegates(self):
        app = _mk_app()
        auth = MagicMock()
        app.register_user(username="u", role=Role.EMPLOYEE, name="N", email="", phone="", password="pw", auth_service=auth)
        auth.register_user.assert_called_once_with(
            username="u", role=Role.EMPLOYEE, name="N", email="", phone_number="", password="pw"
        )
