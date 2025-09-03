class Vehicle:
    def __init__(self, vehicle_id, name, capacity, max_range):
        self.vehicle_id = vehicle_id
        self.name = name
        self.capacity = capacity
        self.max_range = max_range
        self.assignments = []

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
    
    def assign_route(self, route_id, departure_time, arrival_time):
        if not self.is_available_for(departure_time, arrival_time):
            raise ValueError(f"Truck {self.vehicle_id} is busy during this time.")
        self.assignments.append((route_id, departure_time, arrival_time))

    def unassign_route(self, route_id):
        self.assignments = [assignment for assignment in self.assignments if assignment[0] != route_id]

      