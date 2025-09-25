from src.models.map import Map
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.customer import Customer

class DeliveryPackage:
    _next_id = 1
    def __init__(self, start_location: str, end_location: str, weight: float, customer: 'Customer', package_id: int | None = None):
        if not Map.is_valid_location(start_location):
            raise ValueError(f"Invalid start location: {start_location}")
        if not Map.is_valid_location(end_location):
            raise ValueError(f"Invalid end location: {end_location}")
        if start_location == end_location:
            raise ValueError("Start and end locations must be different.")
        if float(weight) <= 0:
            raise ValueError("Weight must be positive.")
        if package_id is None:
            package_id = DeliveryPackage._next_id
            DeliveryPackage._next_id += 1
        self._package_id = package_id
        self.start_location = start_location
        self.end_location = end_location
        self.current_location = start_location
        self.weight = float(weight)
        self.customer = customer

        self.route = None
        self.expected_arrival = None
        self.status = None

    @property
    def package_id(self): return self._package_id
    
    def _set_package_id(self, value: int):
        self._package_id = value

    def info(self):
        """Return a human-readable description of the package."""
        contact_info = f"{self.customer.name} ({self.customer.contact.display_email()}, {self.customer.contact.display_phone()})"
        return (
            f"Package {self.package_id}: {self.start_location} → {self.end_location}, {self.weight:.1f}kg\n"
            f"Customer: {contact_info}\n"
            f"Assigned route: {self.route.route_id if self.route else 'Not assigned'}\n"
            f"Expected arrival: {self.expected_arrival.strftime('%Y-%m-%d %H:%M') if self.expected_arrival else 'Not assigned'}"
        )
