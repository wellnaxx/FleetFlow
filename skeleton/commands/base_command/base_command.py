from abc import ABC, abstractmethod
from core.application_data import ApplicationData

class BaseCommand(ABC):
    def __init__(self, params: list[str], app_data: ApplicationData):
        self._params = params
        self._app_data = app_data

    @property
    def params(self):
        return tuple(self._params)

    @property
    def app_data(self):
        return self._app_data
    
    @abstractmethod
    def execute(self):
        return ""
