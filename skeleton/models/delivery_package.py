from core.map import Map
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.users.customer import Customer

class DeliveryPackage:

    _next_id = 1

    def __init__(self, start_location: str, end_location: str, weight: float, customer: 'Customer') -> None:
        self.start_location = start_location
        self.end_location = end_location
        self.weight = weight
        self.customer = customer._user_id

        self._package_id = DeliveryPackage._next_id
        DeliveryPackage._next_id += 1

        self.route = None
    
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