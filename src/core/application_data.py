from src.models.delivery_route import DeliveryRoute
from src.models.delivery_package import DeliveryPackage
from src.core.vehicle_manager import VehicleManager
from src.core.serialization import dt_to_str, dt_from_str
from src.models.map import Map
from src.models.customer import Customer
from src.models.item_status import ItemStatus
from src.models.contact_info import ContactInfo
from src.core.authz import AuthorizationService, requires, requires_all
from src.models.auth import Permission, Role
from src.models.users.employee import Employee
from src.models.users.manager import Manager
from src.core.paths import resolve_data_path, ensure_data_dir

import json, os, tempfile
from datetime import datetime

class ApplicationData:
    """Holds domain objects and implements business operations for the app."""
    AUTOSAVE_PATH = resolve_data_path("state.json")
    def __init__(self, current_user=None):
        self.authz = AuthorizationService(current_user)
        self.vehicle_manager = VehicleManager()
        self._routes: list[DeliveryRoute] = []
        self._packages: list[DeliveryPackage] = []
        self._users: list[Employee | Manager] = []
        self._customers: list[Customer] = []
        self._customers_by_email: dict[str, Customer] = {}
        self._customers_by_phone: dict[str, Customer] = {}
        self._next_customer_id = 1
        self._next_package_id = 1
        self._next_route_id = 1

    def _gen_customer_id(self): i=self._next_customer_id; self._next_customer_id+=1; return i
    def _gen_package_id(self):  i=self._next_package_id;  self._next_package_id+=1;  return i
    def _gen_route_id(self):    i=self._next_route_id;    self._next_route_id+=1;    return i


    # --- INTERNAL: serialize current state to a dict (no RBAC) ---
    def _dump_state(self) -> dict:
        """Serialize the current in-memory state into a plain dict."""
        return {
            "schema_version": 1,
            "counters": {
                "next_customer_id": getattr(self, "_next_customer_id", 1),
                "next_package_id": getattr(self, "_next_package_id", 1),
                "next_route_id": getattr(self, "_next_route_id", 1),
            },
            "customers": [
                {"customer_id": c.customer_id, "name": c.name, "email": c.email or "", "phone": getattr(c, "phone", "") or ""}
                for c in self._customers
            ],
            "packages": [
                {
                    "package_id": p.package_id,
                    "start": p.start_location,
                    "end": p.end_location,
                    "weight": p.weight,
                    "customer_id": p.customer.customer_id,
                    "route_id": (p.route.route_id if getattr(p, "route", None) else None),
                }
                for p in self._packages
            ],
            "routes": [
                {
                    "route_id": r.route_id,
                    "locations": list(r.locations),
                    "departure_time": dt_to_str(getattr(r, "departure_time", None)),
                    "truck_vehicle_id": (r.truck.vehicle_id if getattr(r, "truck", None) else None),
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
                if os.path.exists(tmp): os.remove(tmp)
            except Exception:
                pass
        return path

    # --- INTERNAL: load dict into current instance (no RBAC) ---
    def _apply_state(self, data: dict) -> None:
        """Load a previously serialized dict into this instance."""
        ver = data.get("schema_version", 1)
        if ver != 1:
            raise ValueError(f"Unsupported state version: {ver}")

        # clear tables
        self._routes.clear()
        self._packages.clear()
        self._customers.clear()
        self._customers_by_email.clear()
        self._customers_by_phone.clear()

        # counters
        ctr = data.get("counters", {})
        self._next_customer_id = int(ctr.get("next_customer_id", 1))
        self._next_package_id  = int(ctr.get("next_package_id", 1))
        self._next_route_id    = int(ctr.get("next_route_id", 1))

        # rebuild entities
        id_to_customer = {}
        from src.models.contact_info import ContactInfo
        from src.models.customer import Customer
        from src.models.delivery_package import DeliveryPackage
        from src.models.delivery_route import DeliveryRoute

        for c in data.get("customers", []):
            ci = ContactInfo(name=c["name"], email=c.get("email",""), phone_number=c.get("phone",""))
            cust = Customer(customer_id=int(c["customer_id"]), contact=ci)
            self._customers.append(cust)
            id_to_customer[cust.customer_id] = cust
            self._index_customer(cust)

        id_to_package = {}
        for p in data.get("packages", []):
            cust = id_to_customer.get(int(p["customer_id"]))
            if not cust:
                raise ValueError(f"Package {p['package_id']} refers to missing customer {p['customer_id']}")
            pkg = DeliveryPackage(p["start"], p["end"], float(p["weight"]), cust)
            pkg._set_package_id(int(p["package_id"])) 
            self._packages.append(pkg)
            id_to_package[pkg.package_id] = pkg
            cust.add_package(pkg)

        id_to_route = {}
        for r in data.get("routes", []):
            dep = dt_from_str(r.get("departure_time"))
            route = DeliveryRoute(*r["locations"], departure_time=dep)
            route.route_id = int(r["route_id"])
            id_to_route[route.route_id] = route
            self._routes.append(route)

        # link trucks and packages
        for r in data.get("routes", []):
            route = id_to_route[int(r["route_id"])]
            v_id = r.get("truck_vehicle_id")
            if v_id is not None:
                truck = self.vehicle_manager.find_by_id(int(v_id))
                if truck:
                    route.truck = truck
                    truck.assign(route, route.start_location)
            for pid in r.get("package_ids", []):
                pkg = id_to_package.get(int(pid))
                if not pkg:
                    raise ValueError(f"Route {route.route_id} refers to missing package {pid}")
                if hasattr(route, "assign_package"):
                    route.assign_package(pkg)
                else:
                    route.packages.append(pkg)
                    pkg.route = route

        # refresh derived fields
        try:
            self.heartbeat()
        except Exception:
            pass

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
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._apply_state(data)
        return f"Loaded state from {abs_path}"

    @requires(Permission.ADMIN_USER)
    def register_user(self, *, username: str, role: Role, name: str, email: str, phone: str, password: str, auth_service):
        """
        Manager-only. Delegates to AuthService to create the account in the user store.
        """
        # NB: pass-through to AuthService; keeps RBAC centralized here.
        return auth_service.register_user(username=username, role=role, name=name, email=email, phone_number=phone, password=password)

    def heartbeat(self, now: datetime | None = None) -> dict:
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
                setattr(route, "status", new_status)
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
                if pos.stop_city == r.end_location and (r.eta_final and now >= r.eta_final):
                    if truck.release(now=now, force=False):
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

            elif pos.kind == "AFTER_END":
                if truck.release(now=now, force=False):
                    released_trucks += 1
                    moved_trucks += 1

            updated_packages += self._update_packages_for_route(r, now)

        return {
            "routes_updated": updated_routes,
            "trucks_moved": moved_trucks,
            "trucks_released": released_trucks,
            "packages_updated": updated_packages,
        }

    def _compute_route_status(self, route, now: datetime) -> str:
        dt = getattr(route, "departure_time", None)
        eta = getattr(route, "eta_final", None)
        if dt is None:
            return "PLANNED"
        if now < dt:
            return "SCHEDULED"
        if eta is not None and now >= eta:
            return "COMPLETED"
        return "IN_PROGRESS"

    def _update_packages_for_route(self, route, now: datetime) -> int:
        """Update status/current_location for all packages assigned to a route."""
        changed = 0

        stop_times = {}
        if route.departure_time is not None:
            for city in route.locations:
                try:
                    stop_times[city] = route.arrival_time_at(city)
                except Exception:
                    pass

        pos_index = {c: i for i, c in enumerate(route.locations)}

        for p in route.packages:
            s, e = p.start_location, p.end_location

            if not hasattr(p, "current_location"):
                setattr(p, "current_location", s)

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
                try:
                    p.expected_arrival = route.arrival_time_at(e)
                except Exception:
                    pass

        return changed

    @staticmethod
    def _set_pkg(p, *, status, current_location) -> int:
        delta = 0
        if getattr(p, "status", None) != status:
            p.status = status
            delta += 1
        if getattr(p, "current_location", None) != current_location:
            p.current_location = current_location
            delta += 1
        return delta

    def _index_customer(self, c: Customer):
        if c.email:
            existing = self._customers_by_email.get(c.email)
            if existing and existing is not c:
                raise ValueError(f"Email already in use by customer id={existing.customer_id}")
            self._customers_by_email[c.email] = c
        if c.phone_number:
            existing = self._customers_by_phone.get(c.phone_number)
            if existing and existing is not c:
                raise ValueError(f"Phone already in use by customer id={existing.customer_id}")
            self._customers_by_phone[c.phone_number] = c

    def _generate_customer_id(self) -> int:
        cid = self._next_customer_id
        self._next_customer_id += 1
        return cid
    
    @staticmethod
    def _same_name(a: str, b: str) -> bool:
        return (a or "").strip().casefold() == (b or "").strip().casefold()

    def _find_or_create_customer(self, name: str, email: str = "", phone: str = "") -> Customer:
        name  = (name or "").strip()
        email = (email or "").strip().lower()
        phone = "".join(ch for ch in (phone or "") if ch.isdigit())

        by_email = self._customers_by_email.get(email) if email else None
        by_phone = self._customers_by_phone.get(phone) if phone else None

        if email and phone:
            if by_email and by_phone:
                if by_email is not by_phone:
                    raise ValueError(
                        f"Email belongs to customer ID: {by_email.customer_id}, "
                        f"and phone belongs to customer ID: {by_phone.customer_id}."
                    )
                if name and not self._same_name(name, by_email.name):
                    raise ValueError(
                        f"Provided name '{name}' does not match existing customer "
                        f"ID {by_email.customer_id} ('{by_email.name}')."
                    )
                return by_email

            if by_email and not by_phone:
                if name and not self._same_name(name, by_email.name):
                    raise ValueError(
                        f"Email already in use by customer ID {by_email.customer_id} ('{by_email.name}')."
                    )
                return by_email 

            if by_phone and not by_email:
                if name and not self._same_name(name, by_phone.name):
                    raise ValueError(
                        f"Phone already in use by customer ID {by_phone.customer_id} ('{by_phone.name}')."
                    )
                return by_phone

        if email and by_email:
            if name and not self._same_name(name, by_email.name):
                raise ValueError(
                    f"Email already in use by customer ID {by_email.customer_id} ('{by_email.name}')."
                )
            return by_email

        if phone and by_phone:
            if name and not self._same_name(name, by_phone.name):
                raise ValueError(
                    f"Phone already in use by customer ID {by_phone.customer_id} ('{by_phone.name}')."
                )
            return by_phone

        if name:
            candidates = [c for c in self._customers if self._same_name(c.name, name)]
            name_only = [c for c in candidates if c.email == "" and c.phone_number == ""]
            if not email and not phone and len(name_only) == 1 and len(candidates) == 1:
                return name_only[0]

        contact_info = ContactInfo(name=name, email=email, phone_number=phone)
        customer = Customer(customer_id=self._generate_customer_id(), contact=contact_info)
        self._customers.append(customer)
        if email:
            self._customers_by_email[email] = customer
        if phone:
            self._customers_by_phone[phone] = customer
        return customer
    
    @requires(Permission.CUSTOMER_VIEW)
    def view_all_customers(self):
        return tuple(self._customers)

    @property
    def customers(self):
        return tuple(self._customers)

    @requires(Permission.ROUTE_CREATE)
    def create_route(self, locations, departure_time):
        if len(locations) < 2:
            raise ValueError("Invalid number of locations. A route must contain at least 2 locations.")
        for c in locations:
            if not Map.is_valid_location(c):
                raise ValueError(f"Invalid location: {c}")
        r = DeliveryRoute(*locations, departure_time=departure_time, route_id=self._gen_route_id())
        self._routes.append(r)
        return r

    def find_route(self, route_id: int):
        for r in self._routes:
            if r.route_id == route_id:
                return r
        return None

    @requires(Permission.ROUTE_REMOVE)
    def remove_route(self, route_id: int):
        r = self.find_route(route_id)
        if not r:
            raise ValueError(f"Route with ID {route_id} not found")
        self._routes.remove(r)
        if r.truck:
            r.truck.release()
        return r

    @requires(Permission.ROUTE_VIEW)
    def view_route(self, route_id: int):
        return self.find_route(route_id)
    
    @requires(Permission.ROUTE_VIEW_IN_PROGRESS)
    def view_routes_in_progress(self, now: datetime | None = None):
        now = now or datetime.now()
        active: list[tuple[DeliveryRoute, object]] = []
        for r in self._routes:
            pos = r.current_position(now)
            if pos.kind in {"AT_STOP", "IN_TRANSIT"}:
                active.append((r, pos))
        return tuple(active)
    
    @requires(Permission.ROUTE_VIEW_ALL)
    def view_all_routes(self):
        return tuple(self._routes)

    @property
    def routes(self):
        return tuple(self._routes)

    @requires(Permission.PACKAGE_CREATE)
    def create_package(self, start, end, weight, name, email=None, phone=None):
        customer = self._find_or_create_customer(name, email or "", phone or "")
        p = DeliveryPackage(start, end, float(weight), customer, package_id=self._gen_package_id())
        p.status = ItemStatus.TODO
        self._packages.append(p)
        customer.add_package(p)
        return p
    
    @requires_all(Permission.PACKAGE_REMOVE, Permission.PACKAGE_VIEW)
    def remove_package(self, package_id: int):
        """Remove a package by ID.

        Detaches it from a route if attached, then removes it from registry.

        Args:
            package_id: The package identifier.

        Returns:
            The removed package object.

        Raises:
            ValueError: If the package does not exist.
            PermissionError: If the current user lacks rights.
        """
        pkg = self.view_package(package_id)
        if not pkg:
            raise ValueError(f"Package with ID {package_id} not found")

        r = getattr(pkg, "route", None)
        if r:
            if hasattr(r, "packages"):
                r.packages = [pp for pp in r.packages if pp.package_id != package_id]
            pkg.route = None

        self._packages.remove(pkg)
        return pkg

    @requires(Permission.PACKAGE_VIEW)
    def view_package(self, package_id: int):
        for p in self._packages:
            if p.package_id == package_id:
                return p
        return None

    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def view_unassigned_packages(self):
        return tuple(
            p for p in self._packages
            if getattr(p, "route", None) is None
        )
    
    @requires(Permission.PACKAGE_VIEW_ALL)
    def view_all_packages(self):
        return tuple(self._packages)

    @property
    def packages(self):
        return tuple(self._packages)
    
    @requires(Permission.ROUTE_ASSIGN_PACKAGE)
    def assign_packages_to_route(self, route_id: int, package_ids: list[int]):
        route = self.find_route(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found.")

        seen = set()
        successes, errors = [], []

        for pid in package_ids:
            if pid in seen:
                continue
            seen.add(pid)

            package = getattr(self, "get_package", None)
            package = package(pid) if package else self.view_package(pid)

            if not package:
                errors.append(f"Package {pid} not found.")
                continue
            if getattr(package, "route", None):
                errors.append(f"Package {pid} is already on route {package.route.route_id}.")
                continue

            try:
                if hasattr(route, "assign_package"):
                    route.assign_package(package)
                else:
                    route.packages.append(package)
                    package.route = route

                if getattr(route, "departure_time", None):
                    try:
                        eta_dt = route.arrival_time_at(package.end_location)
                        eta_str = (
                            eta_dt.strftime("%Y-%m-%d %H:%M")
                            if hasattr(eta_dt, "strftime")
                            else str(eta_dt)
                        )
                    except Exception:
                        eta_str = "N/A"
                    successes.append(
                        f"Assigned package {package.package_id} to route {route.route_id}. ETA: {eta_str}"
                    )
                else:
                    successes.append(
                        f"Assigned package {package.package_id} to route {route.route_id}. "
                        "ETA: N/A (route unscheduled)"
                    )
            except Exception as e:
                errors.append(f"{pid}: {e}")

        if not successes and errors:
            raise ValueError("No packages could be assigned:\n- " + "\n- ".join(errors))

        parts = []
        if successes:
            parts.append("\n".join(successes))
        if errors:
            parts.append("Failed:\n- " + "\n- ".join(errors))
        return parts

    @requires(Permission.ROUTE_ASSIGN_TRUCK)
    def assign_truck_to_route(self, vehicle_id: int, route_id: int):
        route = self.find_route(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        truck = self.vehicle_manager.find_by_id(vehicle_id)
        if not truck:
            raise ValueError(f"Truck with ID {vehicle_id} not found")

        if route.departure_time is None:
            route.schedule(datetime.now())


        ok, reason = self.vehicle_manager.is_suitable_for_route(truck, route)
        if not ok:
            raise ValueError(
                f"Truck {vehicle_id} is not suitable for route {route_id}: {reason}. "
                f"Use 'findsuitabletrucksforroute {route_id}' to list options."
            )

        route.truck = truck
        truck.assign(route, route.start_location)

        return route

    @requires_all(
        Permission.PACKAGE_FIND_ROUTE_FOR,
        Permission.PACKAGE_VIEW,           
        Permission.ROUTE_VIEW               
    )
    def find_suitable_routes_for_package(self, package_id: int):
        """
        Returns a list of dicts: [{ 'route': r, 'eta': eta_dt or None, 'capacity_left': float|None }]
        A route is suitable if start/end appear in order and (if truck assigned) it has enough remaining capacity.
        """
        pkg = self.view_package(package_id) 
        if not pkg:
            raise ValueError(f"Package with ID {package_id} not found.")

        results = []
        now = datetime.now()

        for r in self._routes:
            locs = r.locations
            try:
                si = locs.index(pkg.start_location)
                ei = locs.index(pkg.end_location)
                if si >= ei:
                    continue
            except ValueError:
                continue

            capacity_left = None
            if r.truck:
                capacity_left = r.truck.capacity - r.total_assigned_weight()
                if capacity_left < pkg.weight:
                    continue

            eta = None
            try:
                eta = r.arrival_time_at(pkg.end_location)
            except Exception:
                eta = None

            results.append({"route": r, "eta": eta, "capacity_left": capacity_left})

        results.sort(key=lambda x: (x["eta"] is None, x["eta"] or datetime.max))
        return results

    @requires(Permission.ROUTE_FIND_TRUCK_FOR)
    def find_suitable_trucks_for_route(self, route_id: int):
        route = self.find_route(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        return self.vehicle_manager.find_available_for_route(route)

    @requires(Permission.TRUCK_VIEW)
    def view_all_trucks(self):
        return tuple(self.vehicle_manager.list_fleet())
