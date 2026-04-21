import contextlib
import json
import os
import tempfile
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.adapters.driven.persistence.json.paths import resolve_data_path
from src.adapters.driven.persistence.json.serialization import dt_from_str, dt_to_str
from src.application.services.auth_service import AuthService
from src.application.services.authorization import AuthorizationService, requires
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.users.user import User
from src.domain.enums.auth import Permission, Role
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.services.vehicle_manager import VehicleManager

if TYPE_CHECKING:
    from src.domain.entities.truck import Truck
    from src.domain.entities.users.employee import Employee
    from src.domain.entities.users.manager import Manager


class ApplicationData:
    """Holds domain objects and implements business operations for the app."""

    AUTOSAVE_PATH: str = resolve_data_path("state.json")

    def __init__(self, current_user: User | None = None) -> None:
        self.authz = AuthorizationService(current_user)
        self.vehicle_manager = VehicleManager()
        self._routes: list[DeliveryRoute] = []
        self._packages: list[DeliveryPackage] = []
        self._users: list[Employee | Manager] = []
        self._customers: list[Customer] = []
        self._customers_by_email: dict[str, Customer] = {}
        self._customers_by_phone: dict[str, Customer] = {}
        self._next_customer_id: int = 1
        self._next_package_id: int = 1
        self._next_route_id: int = 1

    def _gen_customer_id(self) -> int:
        i = self._next_customer_id
        self._next_customer_id += 1
        return i

    def _gen_package_id(self) -> int:
        i = self._next_package_id
        self._next_package_id += 1
        return i

    def _gen_route_id(self) -> int:
        i = self._next_route_id
        self._next_route_id += 1
        return i

    # --- INTERNAL: serialize current state to a dict (no RBAC) ---
    def _dump_state(self) -> dict[str, Any]:
        """Serialize the current in-memory state into a plain dict."""
        return {
            "schema_version": 1,
            "counters": {
                "next_customer_id": getattr(self, "_next_customer_id", 1),
                "next_package_id": getattr(self, "_next_package_id", 1),
                "next_route_id": getattr(self, "_next_route_id", 1),
            },
            "customers": [
                {
                    "customer_id": c.customer_id,
                    "name": c.name,
                    "email": c.email or "",
                    "phone": c.phone_number or "",
                }
                for c in self._customers
            ],
            "packages": [
                {
                    "package_id": p.package_id,
                    "start": p.start_location,
                    "end": p.end_location,
                    "weight": p.weight,
                    "customer_id": p.customer.customer_id,
                    "route_id": (p.route.route_id if p.route is not None else None),
                }
                for p in self._packages
            ],
            "routes": [
                {
                    "route_id": r.route_id,
                    "locations": list(r.locations),
                    "departure_time": dt_to_str(getattr(r, "departure_time", None)),
                    "truck_vehicle_id": (r.truck.vehicle_id if r.truck is not None else None),
                    "package_ids": [p.package_id for p in r.packages],
                }
                for r in self._routes
            ],
        }

    # --- INTERNAL: atomic write, no RBAC (for autosave) ---
    def _persist_to_file(self, path: str | None = None) -> str:
        """Atomically write the current state JSON to disk (used by autosave).

        Args:
            path: Target filename or path. If None, uses AUTOSAVE_PATH.
                  Bare filenames are placed under data/.
        Returns:
            The absolute path written.
        """
        data = self._dump_state()
        path = resolve_data_path(path) or self.AUTOSAVE_PATH
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".appstate.", suffix=".json", dir=os.path.dirname(path) or ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)  # atomic on same filesystem
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        return path

    # --- INTERNAL: load dict into current instance (no RBAC) ---
    def _apply_state(self, data: dict[str, Any]) -> None:
        """Load a previously serialized dict into this instance."""
        ver = data.get("schema_version", 1)
        if ver != 1:
            raise ValueError(f"Unsupported state version: {ver}")

        ctr = data.get("counters", {})
        next_customer_id = int(ctr.get("next_customer_id", 1))
        next_package_id = int(ctr.get("next_package_id", 1))
        next_route_id = int(ctr.get("next_route_id", 1))

        # rebuild entities
        from src.domain.entities.customer import Customer as Customer_
        from src.domain.value_objects.contact_info import ContactInfo

        customers: list[Customer] = []
        customers_by_email: dict[str, Customer] = {}
        customers_by_phone: dict[str, Customer] = {}
        id_to_customer: dict[int, Customer_] = {}
        from src.domain.entities.delivery_package import DeliveryPackage
        from src.domain.entities.delivery_route import DeliveryRoute

        for c in data.get("customers", []):
            ci = ContactInfo(name=c["name"], email=c.get("email", ""), phone_number=c.get("phone", ""))
            cust = Customer(customer_id=int(c["customer_id"]), contact=ci)
            customers.append(cust)
            assert cust.customer_id is not None
            id_to_customer[cust.customer_id] = cust
            self._index_customer_record(cust, customers_by_email, customers_by_phone)

        id_to_package: dict[int, DeliveryPackage] = {}
        packages: list[DeliveryPackage] = []
        for p in data.get("packages", []):
            cust = id_to_customer.get(int(p["customer_id"]))
            if not cust:
                raise ValueError(f"Package {p['package_id']} refers to missing customer {p['customer_id']}")
            pkg = DeliveryPackage(p["start"], p["end"], float(p["weight"]), cust, p["package_id"])
            pkg._set_package_id(int(p["package_id"]))  # pyright: ignore[reportPrivateUsage]
            packages.append(pkg)
            id_to_package[pkg.package_id] = pkg
            cust.add_package(pkg)

        id_to_route: dict[int, DeliveryRoute] = {}
        routes: list[DeliveryRoute] = []
        for r in data.get("routes", []):
            dep = dt_from_str(r.get("departure_time"))
            route = DeliveryRoute(*r["locations"], departure_time=dep)
            route.route_id = int(r["route_id"])
            id_to_route[route.route_id] = route
            routes.append(route)

        route_truck_pairs: list[tuple[DeliveryRoute, Truck]] = []
        for r in data.get("routes", []):
            route = id_to_route[int(r["route_id"])]
            v_id = r.get("truck_vehicle_id")
            if v_id is not None:
                truck = self.vehicle_manager.find_by_id(int(v_id))
                if truck is None:
                    raise ValueError(f"Route {route.route_id} refers to missing truck {v_id}")
                route_truck_pairs.append((route, truck))
            for pid in r.get("package_ids", []):
                pkg = id_to_package.get(int(pid))
                if not pkg:
                    raise ValueError(f"Route {route.route_id} refers to missing package {pid}")
                if hasattr(route, "assign_package"):
                    route.assign_package(pkg)
                else:
                    route.packages.append(pkg)
                    pkg.route = route

        self._reset_vehicle_manager_state()
        for route, truck in route_truck_pairs:
            route.truck = truck
            truck.assign(route, route.start_location)

        self._routes = routes
        self._packages = packages
        self._customers = customers
        self._customers_by_email = customers_by_email
        self._customers_by_phone = customers_by_phone
        self._next_customer_id = next_customer_id
        self._next_package_id = next_package_id
        self._next_route_id = next_route_id

        # refresh derived fields
        with contextlib.suppress(Exception):
            self.heartbeat()

    # --- PUBLIC (manager-only) manual commands remain RBAC-guarded ---
    @requires(Permission.APP_SAVE_STATE)
    def save(self, path: str) -> str:
        """Persist the current application state to a JSON file.

        Args:
            path: Target filename or path. Bare filenames go to data/.
        Returns:
            Human-friendly confirmation message.
        """
        abs_path = self._persist_to_file(path)
        return f"Saved state to {abs_path}"

    @requires(Permission.APP_LOAD_STATE)
    def load(self, path: str) -> str:
        """Load application state from a JSON file, replacing current state.

        Args:
            path: Source filename or path. Bare filenames are looked up in data/.
        Returns:
            Human-friendly confirmation message.
        Raises:
            ValueError: If the file does not exist or is invalid.
        """
        abs_path = resolve_data_path(path)
        if not os.path.exists(abs_path):
            raise ValueError(f"State file not found: {abs_path}")
        with open(abs_path, encoding="utf-8") as f:
            data = json.load(f)
        self._apply_state(data)
        return f"Loaded state from {abs_path}"

    @requires(Permission.ADMIN_USER)
    def register_user(
        self,
        *,
        username: str,
        role: Role,
        name: str,
        email: str,
        phone: str,
        password: str,
        auth_service: AuthService,
    ) -> Any:
        """
        Manager-only. Delegates to AuthService to create the account in the user store.
        """
        # NB: pass-through to AuthService; keeps RBAC centralized here.
        return auth_service.register_user(
            username=username, role=role, name=name, email=email, phone_number=phone, password=password
        )

    def heartbeat(self, now: datetime | None = None) -> dict[str, int]:
        """
        Advance state based on real time:
        - Update implicit route 'status' (attached dynamically)
        - Move trucks along routes; auto-release at final arrival
        - Update package status and current_location
        Returns summary counts.
        """
        now = now or datetime.now()
        updated_routes = 0
        moved_trucks = 0
        released_trucks = 0
        updated_packages = 0

        for route in self._routes:
            new_status = self._compute_route_status(route, now)
            if getattr(route, "status", None) != new_status:
                route.status = new_status
                updated_routes += 1

        for truck in self.vehicle_manager.vehicles:
            r = getattr(truck, "route", None)
            if not r:
                continue

            pos = r.current_position(now)

            if pos.kind == "UNSCHEDULED":
                pass

            elif pos.kind == "BEFORE_START":
                if truck.current_location != r.start_location or getattr(truck, "in_transit_to", None):
                    truck.current_location = r.start_location
                    truck.in_transit_to = None
                    moved_trucks += 1

            elif pos.kind == "AT_STOP":
                if pos.stop_city and truck.current_location != pos.stop_city:
                    truck.current_location = pos.stop_city
                    truck.in_transit_to = None
                    moved_trucks += 1
                if (
                    pos.stop_city == r.end_location
                    and r.eta_final
                    and now >= r.eta_final
                    and truck.release(now=now, force=False)
                ):
                    released_trucks += 1

            elif pos.kind == "IN_TRANSIT":
                changed = False
                if pos.from_city and truck.current_location != pos.from_city:
                    truck.current_location = pos.from_city
                    changed = True
                if truck.in_transit_to != pos.to_city:
                    truck.in_transit_to = pos.to_city
                    changed |= True
                if changed:
                    moved_trucks += 1

            elif pos.kind == "AFTER_END" and truck.release(now=now, force=False):
                released_trucks += 1
                moved_trucks += 1

            updated_packages += self._update_packages_for_route(r, now)

        return {
            "routes_updated": updated_routes,
            "trucks_moved": moved_trucks,
            "trucks_released": released_trucks,
            "packages_updated": updated_packages,
        }

    def _compute_route_status(self, route: DeliveryRoute, now: datetime) -> str:
        dt = getattr(route, "departure_time", None)
        eta = getattr(route, "eta_final", None)
        if dt is None:
            return "PLANNED"
        if now < dt:
            return "SCHEDULED"
        if eta is not None and now >= eta:
            return "COMPLETED"
        return "IN_PROGRESS"

    def _update_packages_for_route(self, route: DeliveryRoute, now: datetime) -> int:
        """Update status/current_location for all packages assigned to a route."""
        changed = 0

        stop_times: dict[str, datetime] = {}
        if route.departure_time is not None:
            for city in route.locations:
                with contextlib.suppress(Exception):
                    stop_times[city] = route.arrival_time_at(city)

        pos_index = {c: i for i, c in enumerate(route.locations)}

        for p in route.packages:
            s, e = p.start_location, p.end_location

            if not hasattr(p, "current_location"):
                p.current_location = s

            if route.departure_time is None:
                changed += self._set_pkg(p, status=ItemStatus.TODO, current_location=s)
                continue

            ts = stop_times.get(s)
            te = stop_times.get(e)

            if ts and now < ts:
                changed += self._set_pkg(p, status=ItemStatus.TODO, current_location=s)

            elif te and now >= te:
                changed += self._set_pkg(p, status=ItemStatus.DONE, current_location=e)

            else:
                last_city = s
                if ts:
                    for i in range(pos_index[s], pos_index[e] + 1):
                        city = route.locations[i]
                        t_city = stop_times.get(city)
                        if t_city and now >= t_city:
                            last_city = city
                        else:
                            break
                changed += self._set_pkg(p, status=ItemStatus.IN_PROGRESS, current_location=last_city)

            if hasattr(p, "expected_arrival"):
                with contextlib.suppress(Exception):
                    p.expected_arrival = route.arrival_time_at(e)

        return changed

    @staticmethod
    def _set_pkg(p: DeliveryPackage, *, status: str, current_location: str) -> int:
        delta = 0
        if getattr(p, "status", None) != status:
            p.status = status
            delta += 1
        if getattr(p, "current_location", None) != current_location:
            p.current_location = current_location
            delta += 1
        return delta

    def _index_customer(self, c: Customer) -> None:
        self._index_customer_record(c, self._customers_by_email, self._customers_by_phone)

    @staticmethod
    def _index_customer_record(
        customer: Customer,
        by_email: dict[str, Customer],
        by_phone: dict[str, Customer],
    ) -> None:
        if customer.email:
            existing = by_email.get(customer.email)
            if existing and existing is not customer:
                raise ValueError(f"Email already in use by customer id={existing.customer_id}")
            by_email[customer.email] = customer
        if customer.phone_number:
            existing = by_phone.get(customer.phone_number)
            if existing and existing is not customer:
                raise ValueError(f"Phone already in use by customer id={existing.customer_id}")
            by_phone[customer.phone_number] = customer

    def _reset_vehicle_manager_state(self) -> None:
        vehicles = getattr(self.vehicle_manager, "vehicles", None)
        if vehicles is None:
            return

        with contextlib.suppress(Exception):
            self.vehicle_manager.disperse_trucks()

        for truck in vehicles:
            truck.route = None
            truck.status = TruckStatus.FREE
            truck.busy_from = None
            truck.busy_until = None
            truck.in_transit_to = None

    @requires(Permission.CUSTOMER_VIEW)
    def view_all_customers(self) -> tuple[Customer, ...]:
        return tuple(self._customers)

    @property
    def customers(self) -> tuple[Customer, ...]:
        return tuple(self._customers)


    @property
    def packages(self) -> tuple[DeliveryPackage, ...]:
        return tuple(self._packages)


    @property
    def customer_store(self) -> list[Customer]:
        return self._customers

    @property
    def customer_email_store(self) -> dict[str, Customer]:
        return self._customers_by_email

    @property
    def customer_phone_store(self) -> dict[str, Customer]:
        return self._customers_by_phone

    @property
    def package_store(self) -> list[DeliveryPackage]:
        return self._packages

    @property
    def route_store(self) -> list[DeliveryRoute]:
        return self._routes

    def allocate_customer_id(self) -> int:
        return self._gen_customer_id()

    def allocate_package_id(self) -> int:
        return self._gen_package_id()

    def allocate_route_id(self) -> int:
        return self._gen_route_id()
