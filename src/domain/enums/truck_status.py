from typing import ClassVar


class TruckStatus:
    FREE: str = "Free"
    ON_THE_WAY: str = "On the way"
    STATUSES: ClassVar[list[str]] = [FREE, ON_THE_WAY]

    @classmethod
    def from_string(cls, s: str) -> str:
        s = s.strip().lower()
        if s in ("free", "available"):
            return cls.FREE
        if s in ("on_the_way", "busy", "on the way"):
            return cls.ON_THE_WAY
        raise ValueError("Invalid truck status")
