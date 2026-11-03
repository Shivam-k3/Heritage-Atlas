from datetime import datetime

from app.services.trails import group_visits


def test_group_visits_keeps_one_stop_per_site_in_capture_order():
    rows = [
        {
            "site_id": 2,
            "captured_at": datetime(2026, 1, 2, 9, 0),
            "usable": True,
        },
        {
            "site_id": 1,
            "captured_at": datetime(2026, 1, 1, 8, 0),
            "usable": True,
        },
        {
            "site_id": 2,
            "captured_at": datetime(2026, 1, 3, 10, 0),
            "usable": True,
        },
    ]
    assert group_visits(rows) == [
        {"site_id": 2, "visit_date": datetime(2026, 1, 2).date()},
        {"site_id": 1, "visit_date": datetime(2026, 1, 1).date()},
    ]


def test_group_visits_skips_unusable_rows():
    rows = [
        {"site_id": 1, "captured_at": None, "usable": False},
        {"site_id": 2, "captured_at": datetime(2026, 1, 1), "usable": False},
    ]
    assert group_visits(rows) == []
