class Map:
    _locations = ["SYD", "MEL", "ADL", "ASP", "BRI", "DAR", "PER"]

    _distances = _distances = {
        ("SYD", "MEL"): 877,
        ("SYD", "ADL"): 1376,
        ("SYD", "ASP"): 2762,
        ("SYD", "BRI"): 909,
        ("SYD", "DAR"): 3935,
        ("SYD", "PER"): 4016,
        ("MEL", "ADL"): 725,
        ("MEL", "ASP"): 2255,
        ("MEL", "BRI"): 1765,
        ("MEL", "DAR"): 3752,
        ("MEL", "PER"): 3509,
        ("ADL", "ASP"): 1530,
        ("ADL", "BRI"): 1927,
        ("ADL", "DAR"): 3027,
        ("ADL", "PER"): 2785,
        ("ASP", "BRI"): 2993,
        ("ASP", "DAR"): 1497,
        ("ASP", "PER"): 2481,
        ("BRI", "DAR"): 3426,
        ("BRI", "PER"): 4311,
        ("DAR", "PER"): 4025,
    }

    @classmethod
    def get_locations(cls):
        return cls._locations.copy()

    @classmethod
    def get_distance(cls, city_a, city_b):
        if city_a.strip().upper() == city_b.strip().upper():
            return 0
        
        key = (city_a.strip().upper(), city_b.strip().upper())
        reverse_key = (city_b.strip().upper(), city_a.strip().upper())

        if key in cls._distances:
            return cls._distances[key]
        elif reverse_key in cls._distances:
            return cls._distances[reverse_key]
        else:
            raise ValueError(f"No known distance between {city_a} and {city_b}")
        
    @classmethod
    def is_valid_location(cls, location):
        return location.strip().upper() in cls._locations
        