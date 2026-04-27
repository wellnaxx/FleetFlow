from enum import StrEnum


class TruckStatus(StrEnum):
    FREE = "Free"
    ON_THE_WAY = "On the way"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(status.value for status in cls)
