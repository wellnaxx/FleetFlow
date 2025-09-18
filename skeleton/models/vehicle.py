from errors.errors import CapacityError, RangeError
from models.item_status import ItemStatus
from models.vehicle_status import VehicleStatus
from datetime import datetime, timedelta

class Vehicle:
    def __init__(self, vehicle_id, name, capacity, max_range):
        self.vehicle_id = vehicle_id
        self.name = name
        self.capacity = capacity
        self.max_range = max_range
        self.assignments = []
        self.status = VehicleStatus.AVAILABLE
        self.current_location = None

    @property
    def vehicle_id(self):
        return self._vehicle_id
    
    @vehicle_id.setter
    def vehicle_id(self, value):
        try:
            self._vehicle_id = int(value)
        except ValueError:
            raise ValueError("Invalid vehicle id. Vehicle id must be an integer.")
        if self._vehicle_id < 1001 or self._vehicle_id > 1040:
            raise ValueError("Invalid vehicle id. Vehicle id must be in range 1001-1040")
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        if value not in {"Scania", "Man", "Actros"}:
            raise ValueError("Invalid vehicle name. Vehicle name must be 'Scania', 'Man', or 'Actros'.")
        self._name = value
    
    @property
    def capacity(self):
        return self._capacity
    
    @capacity.setter
    def capacity(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValueError("Invalid vehicle capacity. Capacity must be an integer.")
        
        if value <= 0:
            raise ValueError("Invalid capacity. Capacity must be a positive integer.")
        
        self._capacity = value
    
    @property
    def max_range(self):
        return self._max_range
    
    @max_range.setter
    def max_range(self, value):
        try:
            value = int(value)
        except ValueError:
            raise ValueError("Invalid vehicle max range. Max range must be an integer.")
        
        if value <= 0:
            raise ValueError("Invalid max range. Max range must be a positive integer.")
        
        self._max_range = value
    
    def is_available_for(self, departure_time, arrival_time):
        for _, assigned_departure, assigned_arrival in self.assignments:
            if not (arrival_time <= assigned_departure or departure_time >= assigned_arrival):
                return False
        return True
    
    def can_take_route(self, route):
        total_weight = sum(package.weight for package in route._packages)
        if total_weight > self.capacity:
            raise CapacityError(f"Over capacity: {total_weight}/{self.capacity} kg")
        if route.calculate_km > self.max_range:
            raise RangeError(f"Over max range: {route.calculate_km}/{self.max_range} km")
        return True
    
    def assign_route(self, route, route_distance, departure_time=None, arrival_time=None):
        if not self.is_available_for(departure_time, arrival_time):
            raise ValueError(f"Truck {self.vehicle_id} is busy during this time.")
        try:
            self.can_take_route(route)
        except CapacityError as e:
            raise ValueError(f"Truck {self.vehicle_id} cannot take this route (capacity issue). {e}")
        except RangeError as e:
            raise ValueError(f"Truck {self.vehicle_id} cannot take this route (range issue). {e}")
        route._departure_time = datetime.now()
        travel_hours = route_distance / route._average_speed_kmh
        route._arrival_time = route._departure_time + timedelta(hours=travel_hours)
        self.assignments.append((route, departure_time, arrival_time))
        route._truck = self
        route._status = ItemStatus.IN_PROGRESS

    def unassign_route(self, route_id):
        self.assignments = [(route, departure_time, arrival_time) for (route, departure_time, arrival_time) in self.assignments if route.route_id != route_id]

    def finish_assignment(self, route_id):
        for (route, _, _) in self.assignments:
            if route.route_id == route_id:
                route.status = ItemStatus.DONE
                for package in route._packages:
                    package.status = ItemStatus.DONE
                return
        raise ValueError(f"Route {route_id} not found in assignments")

    def info(self):
        for _, departure_time, arrival_time in self.assignments:
            if departure_time <= datetime.now() <= arrival_time:
                self.status = VehicleStatus.BUSY
                break

        assignment_str = "\n".join(
            f"  - Route {route.route_id}: {departure_time.strftime('%Y-%m-%d %H:%M')} → {arrival_time.strftime('%Y-%m-%d %H:%M')}"
            for route, departure_time, arrival_time in self.assignments) or "   None"
            
        return (
            f"Truck ID: {self.vehicle_id}\n"
            f"Name: {self.name}\n"
            f"Capacity: {self.capacity} kg\n"
            f"Max Range: {self.max_range} km\n"
            f"Status: {self.status}\n"
            f"Assignments:\n{assignment_str}"
        )