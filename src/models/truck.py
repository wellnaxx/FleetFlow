from src.models.truck_status import TruckStatus
from datetime import datetime

class Truck:
    def __init__(self, vehicle_id: int, name: str, capacity: int, max_range: int):
        if name not in ("Scania","Man","Actros"):
            raise ValueError("Truck name must be Scania, Man or Actros")
        self.vehicle_id = vehicle_id
        self.name = name
        self.capacity = int(capacity)
        self.max_range = int(max_range)
        self.status = TruckStatus.FREE
        self.current_location = None
        self.route = None
        self.busy_from: datetime | None = None
        self.busy_until: datetime | None = None
        self.in_transit_to: str | None = None

    def is_free(self):
        return self.status == TruckStatus.FREE

    def assign(self, route, start_location: str | None = None) -> None:
        """Record the assignment window."""
        self.route = route
        self.status = TruckStatus.ON_THE_WAY
        self.busy_from = route.departure_time
        self.busy_until = route.eta_final
        self.in_transit_to = None

    def release(self, *, now: datetime | None = None, force: bool = False) -> bool:
        """
        Finish the current route (if any), moving the truck to the route's end city
        and marking it FREE. Returns True if a change was made, False otherwise.

        - If force=False (default), only releases when now >= route.eta_final.
        - If force=True, releases immediately (admin override).
        """
        if self.route is None:
            self.status = TruckStatus.FREE
            self.in_transit_to = None
            self.busy_from = None
            self.busy_until = None
            return False

        if not force:
            now = now or datetime.now()
            eta = getattr(self.route, "eta_final", None)
            if eta is None or now < eta:
                return False

        end_city = getattr(self.route, "end_location", None)
        if end_city:
            self.current_location = end_city

        self.route = None
        self.status = TruckStatus.FREE
        self.in_transit_to = None
        self.busy_from = None
        self.busy_until = None
        return True

    def info(self) -> str:
        return (
            f"Vehicle ID: {self.vehicle_id}\n"
            f"Name: {self.name}\n"
            f"Capacity: {self.capacity}\n"
            f"Max range: {self.max_range}\n"
            f"Status: {self.status}\n"
            f"Location: {self.current_location or 'Unknown'}"
        )
