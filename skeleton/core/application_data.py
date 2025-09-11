from models.users.customer import Customer
from models.users.employee import Employee
from models.users.manager import Manager
from models.delivery_package import DeliveryPackage
from models.delivery_route import DeliveryRoute
from core.vehicle_manager import VehicleManager


from datetime import datetime


class ApplicationData:
    def __init__(self):
        self.vehicle_manager = VehicleManager()
        self._customers = []
        self._employees = []
        self._managers = []
        self._delivery_packages = []
        self._routes = []


    @property
    def routes(self):
        return tuple(self._routes)

    def create_route(self, locations: list[str]):
        route = DeliveryRoute(*locations)
        self._routes.append(route)
        return route

    def remove_route(self, route_id):
        self._routes.remove(route_id)

    def find_route(self, route_id):
        for route in self._routes:
            if route.route_id == int(route_id):
                return route
        return None

    def view_routes(self):
        return [route.info() for route in self._routes]
    
    def create_package(self, start_location, end_location, weight, name, email, phone):
        customer = self.find_customer(name, email, phone)
        if not customer:
            customer = self.create_customer(name, email, phone)
        package = DeliveryPackage(start_location, end_location, weight, customer)
        self._delivery_packages.append(package)
        customer.add_package(package)
        return package
    
    def view_package(self, package_id):
        for package in self._delivery_packages:
            if package.package_id == package_id:
                return package
        return None
        

    def find_customer(self, name=None, email=None, phone=None):
        for customer in self._customers:
            if (name and customer.name == name) or (email and customer.email == email) or (phone and customer.phone == phone):
                return customer
        return None
    
    def create_customer(self, name, email, phone_number):
        if not self.find_customer(name, email, phone_number):
            customer = Customer(name, email=None, phone_number=None)
            self._customers.append(customer)
            return customer
        raise ValueError("Customer already exists")
    
    # def advance_status(self):
    #     if self._status != ItemStatus.DONE:
    #         self._status = ItemStatus.next(self.status)
    #     raise ValueError(f"Can't change status, already at {self._status}")
    
    # def revert_status(self):
    #     if self._status != ItemStatus.TODO:
    #         self._status = ItemStatus.previous(self.status)
    #     raise ValueError(f"Can't change status, already at {self._status}")
    
    

