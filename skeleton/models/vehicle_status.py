class VehicleStatus:
    AVAILABLE = "Available"
    BUSY =  "Busy"
    STATUSES = [AVAILABLE, BUSY]

    @classmethod
    def from_string(cls, status_string):
        status_string = status_string.upper()
        if status_string not in cls.STATUSES:
            raise ValueError(f"Wrong status: {status_string}")
        return status_string