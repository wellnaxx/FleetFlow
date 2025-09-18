from datetime import datetime, timedelta
from models.vehicle import Vehicle
from models.delivery_package import DeliveryPackage
from models.item_status import ItemStatus
from core.map import Map

class DeliveryRoute:
    _next_id = 1
    _average_speed_kmh = 87

    def __init__(self, *locations, departure_time=None):
        self._locations = list(locations)
        self._starting_location = self._locations[0]
        self._end_location = self._locations[-1]
        self._departure_time = departure_time
        self._arrival_time = None
        self._truck = None
        self._packages = []
        self._status = ItemStatus.TODO

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
        return self._truck
    
    @property
    def calculate_km(self):
        total = 0
        for x in range(len(self._locations) - 1):
            a = self._locations[x]
            b = self._locations[x + 1]
            total += Map.get_distance(a, b)
        return total
    
    @property
    def status(self):
        return self._status

    def assign_truck(self, truck: Vehicle, route_distance_km: int):
        if not self._departure_time:
            self._departure_time = datetime.now()
        travel_hours = route_distance_km / self._average_speed_kmh
        self._arrival_time = self._departure_time + timedelta(hours=travel_hours)
    
        truck.assign_route(self._route_id, self._departure_time, self._arrival_time)
        self._truck = truck

    def can_accept_package(self, package):
        try:
            start_index = self._locations.index(package.start_location)
            end_index = self._locations.index(package.end_location)
        except ValueError:
            return False
        
        if start_index >= end_index:
            return False
        
        if self._truck:
            total_weight = sum(package.weight for package in self._packages) + package.weight
            if total_weight > self._truck.capacity:
                return False
        return True
    
    def add_package(self, package: DeliveryPackage):
        if not isinstance(package, DeliveryPackage):
            raise TypeError("Only DeliveryPackage instances can be added")
        if package in self._packages:
            raise ValueError(f"Package {package.package_id} is already assigned to this route.")
        if package.route is not None:
            raise ValueError(f"Package {package.package_id} is already assigned to route {package.route.route_id}.")
        
        if not self.can_accept_package(package):
            raise ValueError("Package cannot be assigned to this route")
        self._packages.append(package)
        package.route = self
        package.status = ItemStatus.IN_PROGRESS

    def complete_route(self):
        self.arrival_time = datetime.now()
        for package in self._packages:
            package.status = ItemStatus.DONE

    def info(self):
        return (
            f"Route ID: {self.route_id}\n"
            f"Truck ID: {self.truck.vehicle_id if self.truck else 'Not assigned'}\n"
            f"Start_location: {self._starting_location}\n"
            f"End_location: {self._end_location}\n"
            f"Departure time: {self.departure_time.strftime('%Y-%m-%d %H:%M')if self.departure_time else 'Not assigned'}\n"
            f"Arrival time: {self.arrival_time.strftime('%Y-%m-%d %H:%M') if self.arrival_time else 'Not assigned'}\n"
            f"Distance: {self.calculate_km} km"
        )

