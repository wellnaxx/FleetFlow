from models.users.customer import Customer
from models.users.employee import Employee
from models.users.manager import Manager
from models.delivery_package import DeliveryPackage
from models.delivery_route import DeliveryRoute
from core.vehicle_manager import VehicleManager


class ApplicationData:
    def __init__(self):
        self.vehicle_manager = VehicleManager()
        self._customers = []
        self._employees = []
        self._managers = []
        self._delivery_packages = []
        self._routes = []


    