from abc import ABC, abstractmethod
class BaseCommand(ABC):
    """Abstract base for all commands: holds params and app context."""
    def __init__(self, params, app_data, auth):
        self._params = params
        self._app_data = app_data
        self._auth = auth

    @property
    def params(self):
        return tuple(self._params)

    @property
    def app_data(self):
        return self._app_data
    
    @property
    def auth(self):
        return self._auth

    @abstractmethod
    def execute(self):
        raise NotImplementedError # pragma: no cover
