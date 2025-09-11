from models.vehicle import Vehicle
from models.delivery_route import DeliveryRoute
from core.map import Map
from collections import defaultdict


class VehicleManager:
    def __init__(self):
        self.vehicles = ([Vehicle(vehicle_id, "Scania", 42000, 8000) for vehicle_id in range(1001, 1011)] + 
                         [Vehicle(vehicle_id, "Man", 37000, 10000) for vehicle_id in range(1011, 1026)] +
                         [Vehicle(vehicle_id, "Actros", 26000, 13000) for vehicle_id in range(1026, 1041)])
        self.disperse_trucks()
        
    def list_fleet(self):
        for truck in self.vehicles:
            print(truck)
            print("Assignments:", truck.assignments)

    def disperse_trucks(self):
        type_groups = defaultdict(list)
        for truck in self.vehicles:
            type_groups[truck.name].append(truck)

        i = 0
        while any(type_groups.values()):
            for vehicle_type in type_groups:
                if type_groups[vehicle_type]:
                    vehicle = type_groups[vehicle_type].pop(0)
                    vehicle.current_location = Map._locations[i % len(Map._locations)]
                    i += 1

    def find_available_trucks(self, route, route_distance, departure_time, arrival_time):
        return [
            truck for truck in self.vehicles if truck.capacity >= sum(package.weight for package in route._packages) and truck.max_range >= route_distance and truck.is_available_for(departure_time, arrival_time) and truck.current_location == route._starting_location
        ]
    
    def assign_truck_to_route(self, truck_id: int, route: DeliveryRoute, route_distance: int):
        truck = next((t for t in self.vehicles if t.vehicle_id == int(truck_id)), None)
        if not truck:
            raise ValueError(f"Truck with ID {truck_id} not found")
        
        truck.assign_route(route, route_distance)
        truck.current_location = route._end_location

    def unassign_truck_from_route(self, truck_id, route_id):
        truck = next((t for t in self.vehicles if t.vehicle_id == truck_id), None)
        if not truck:
            raise ValueError(f"Truck with ID {truck_id} not found")
        
        assignment_exists = any(route[0] == route_id for route in truck.assignments)
        if not assignment_exists:
            raise ValueError(f"Truck {truck_id} is not assigned to route {route_id}")
        truck.unassign_route(route_id)