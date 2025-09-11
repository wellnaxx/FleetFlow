from core.application_data import ApplicationData
from commands.create_route import CreateRoute
from commands.find_route import FindRoute
from commands.remove_route import RemoveRoute
from commands.view_route import ViewRoute
from commands.create_package import CreatePackage
from commands.view_package import ViewPackage
from commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute
from commands.assign_truck_to_route import AssignTruckToRoute

class CommandFactory:
    def __init__(self, data: ApplicationData):
        self._app_data = data

    def create(self, input_line):
        cmd, *params = input_line.split()

        if cmd.lower() == "createroute":
            return CreateRoute(params, self._app_data)

        if cmd.lower() == "findroute":
            return FindRoute(params, self._app_data)

        if cmd.lower() == "removeroute":
            return RemoveRoute(params, self._app_data)

        if cmd.lower() == "viewroute":
            return ViewRoute(params, self._app_data)
        
        if cmd.lower() == "createpackage":
            return CreatePackage(params, self._app_data)
        
        if cmd.lower() == "viewpackage":
            return ViewPackage(params, self._app_data)
        
        if cmd.lower() == "findsuitabletrucksforroute":
            return FindSuitableTrucksForRoute(params, self._app_data)
        
        if cmd.lower() == "assigntrucktoroute":
            return AssignTruckToRoute(params, self._app_data)

        raise ValueError(f'Invalid command name: {cmd}!')