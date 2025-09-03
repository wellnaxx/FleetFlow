from datetime import datetime, timedelta
from models.vehicle import Vehicle
from models.delivery_package import DeliveryPackage

class DeliveryRoute:
    _next_id = 1
    _average_speed_kmh = 87

    def __init__(self, *locations, departure_time=None):
        self._locations = list(locations)
        self._starting_location = self._locations[0]
        self._end_location = self._locations[-1]
        self._departure_time = departure_time or datetime.now()
        self._arrival_time = None
        self._truck = None
        self._packages = []

        self._route_id = DeliveryRoute._next_id
        DeliveryRoute._next_id += 1

    @property
    def route_id(self):
        return self._route_id
    
    @property
    def departure_time(self):
        return self._departure_time
    
    @property
    def arrival_time(self):
        return self._arrival_time
    
    @property
    def truck(self):
        return self.truck

    def assign_truck(self, truck: Vehicle, route_distance_km: int):
        travel_hours = route_distance_km / self._average_speed_kmh
        self._arrival_time = self._departure_time + timedelta(hours=travel_hours)
    
        truck.assign_route(self._route_id, self._departure_time, self._arrival_time)
        self._truck = truck
    
    def add_package(self, package: DeliveryPackage):
        if not isinstance(package, DeliveryPackage):
            raise TypeError("Only DeliveryPackage instances can be added")
        if package in self._packages:
            raise ValueError(f"Package {package.package_id} is already assigned to this route.")
        if package.route is not None:
            raise ValueError(f"Package {package.package_id} is already assigned to route {package.route.route_id}.")
        self._packages.append(package)
        package.route = self