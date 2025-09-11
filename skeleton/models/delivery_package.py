from core.map import Map
from models.item_status import ItemStatus
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.users.customer import Customer

class DeliveryPackage:

    _next_id = 1

    def __init__(self, start_location: str, end_location: str, weight: float, customer: 'Customer') -> None:
        self.start_location = start_location
        self.end_location = end_location
        self.weight = weight
        self.customer = customer

        self._package_id = DeliveryPackage._next_id
        DeliveryPackage._next_id += 1

        self.route = None
        self.status = ItemStatus.TODO
    
    @property
    def start_location(self):
        return self._start_location
    
    @start_location.setter
    def start_location(self, value):
        if not Map.is_valid_location(value):
            raise ValueError(f"Invalid start location: {value}")
        self._start_location = value
    
    @property
    def end_location(self):
        return self._end_location
    
    @end_location.setter
    def end_location(self, value):
        if not Map.is_valid_location(value):
            raise ValueError(f"Invalid end location: {value}")
        self._end_location = value

    @property
    def weight(self):
        return self._weight
    
    @weight.setter
    def weight(self, value):
        try:
            value = float(value)
        except ValueError:
            raise ValueError("Invalid weight! Weight must be a real number!")
        if value < 0:
            raise ValueError("Weight cannot be a negative number!")
        self._weight = value

    @property
    def package_id(self):
        return self._package_id
    
    @property
    def route(self):
        return self._route
    
    @route.setter
    def route(self, value):
        from models.delivery_route import DeliveryRoute
        if value is not None and not isinstance(value, DeliveryRoute):
            raise ValueError("Route must be a DeliveryRoute object or None.")
        self._route = value

    @property
    def contact_info(self):
        return f"{self.customer.name} ({self.customer.email}, {self.customer.phone_number})"
    
    @property
    def calculate_km(self, start_location, end_location):
        return Map.get_distance(start_location, end_location)
    
    def info(self):
        return(
            f"Package id: {self.package_id}\n"
            f"Start location: {self.start_location}\n"
            f"End location: {self.end_location}\n"
            f"Weight: {self.weight}\n"
            f"Customer contacts: {self.contact_info}\n"
            f"Status: {self.status}\n"
            f"Departure time: {self.route.departure_time if self.route else 'Not assigned to a route'}\n"
            f"Arrival time: {self.route.departure_time + timedelta(hours=self.calculate_km / self.route._average_speed_kmh) if self.route else 'Not assigned to a route'}"
        )
    
