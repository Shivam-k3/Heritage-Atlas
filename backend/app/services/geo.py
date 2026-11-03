"""Straight-line distance helpers for Explorer Trails."""

from collections.abc import Sequence
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two WGS84 points."""
    for value, low, high, name in (
        (lat1, -90, 90, "lat1"),
        (lat2, -90, 90, "lat2"),
        (lon1, -180, 180, "lon1"),
        (lon2, -180, 180, "lon2"),
    ):
        if not low <= value <= high:
            raise ValueError(f"{name} out of range: {value}")
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def missing_coordinate_sites(stops: Sequence[dict]) -> list[int]:
    """Unique site ids that cannot take part in distance calculation, in stop order."""
    missing: list[int] = []
    for stop in stops:
        if None in (stop.get("lat"), stop.get("lon")):
            site_id = int(stop["site_id"])
            if site_id not in missing:
                missing.append(site_id)
    return missing


def trail_legs(stops: Sequence[dict]) -> list[dict[str, int | float]]:
    """Return legs for stops that have coordinates. Stops must be ordered."""
    legs: list[dict[str, int | float]] = []
    for start, end in zip(stops, stops[1:], strict=False):
        if None in (start.get("lat"), start.get("lon"), end.get("lat"), end.get("lon")):
            continue
        legs.append(
            {
                "from": int(start["site_id"]),
                "to": int(end["site_id"]),
                "km": round(
                    haversine_km(
                        float(start["lat"]),
                        float(start["lon"]),
                        float(end["lat"]),
                        float(end["lon"]),
                    ),
                    2,
                ),
            }
        )
    return legs
