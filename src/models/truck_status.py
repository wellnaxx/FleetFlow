class TruckStatus:
    FREE = "Free"
    ON_THE_WAY = "On the way"
    STATUSES = [FREE, ON_THE_WAY]

    @classmethod
    def from_string(cls, s: str):
        s = s.strip().lower()
        if s in ("free","available"):
            return cls.FREE
        if s in ("on_the_way","busy","on the way"):
            return cls.ON_THE_WAY
        raise ValueError("Invalid truck status")
