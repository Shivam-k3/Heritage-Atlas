import pytest
from app.services.geo import haversine_km, missing_coordinate_sites, trail_legs


def test_one_degree_of_latitude_is_about_111_km():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)


def test_same_point_is_zero():
    assert haversine_km(23.8593, 72.1018, 23.8593, 72.1018) == 0.0


def test_out_of_range_coordinates_are_rejected():
    with pytest.raises(ValueError):
        haversine_km(91, 0, 0, 0)
    with pytest.raises(ValueError):
        haversine_km(0, 181, 0, 0)


def test_trail_legs_skip_stops_without_coordinates():
    stops = [
        {"site_id": 1, "lat": 0.0, "lon": 0.0},
        {"site_id": 2, "lat": None, "lon": None},
        {"site_id": 3, "lat": 1.0, "lon": 0.0},
    ]
    assert trail_legs(stops) == []


def test_missing_coordinate_sites_are_reported_once_in_stop_order():
    stops = [
        {"site_id": 4, "lat": None, "lon": None},
        {"site_id": 2, "lat": 1.0, "lon": 1.0},
        {"site_id": 4, "lat": None, "lon": None},
    ]
    assert missing_coordinate_sites(stops) == [4]


def test_trail_legs_are_ordered_and_rounded():
    stops = [
        {"site_id": 7, "lat": 0.0, "lon": 0.0},
        {"site_id": 9, "lat": 1.0, "lon": 0.0},
    ]
    legs = trail_legs(stops)
    assert len(legs) == 1
    assert (legs[0]["from"], legs[0]["to"]) == (7, 9)
    assert legs[0]["km"] == pytest.approx(111.2, abs=0.01)
