from math import asin, cos, radians, sin, sqrt
from random import SystemRandom


def generate_session_code() -> str:
    return f"{SystemRandom().randint(0, 9999):04d}"


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6371000
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c

