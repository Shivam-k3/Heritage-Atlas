from fastapi.testclient import TestClient


def _site(client: TestClient, name: str, lat: float, lon: float) -> int:
    response = client.post(
        "/sites",
        json={"name": name, "region": "Gujarat", "category": "stepwell", "lat": lat, "lon": lon},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_trail_flow_reorder_journal_and_summary(client: TestClient, db):
    first = _site(client, "Rani ki Vav", 23.8593, 72.1018)
    second = _site(client, "Adalaj Stepwell", 23.1667, 72.5833)

    trail = client.post("/trails", json={"title": "Stepwell weekend", "created_by": "Asha"})
    assert trail.status_code == 201
    trail_id = trail.json()["id"]

    stop_one = client.post(
        f"/trails/{trail_id}/stops",
        json={"site_id": first, "visit_date": "2026-10-31", "note": "Original note one"},
    ).json()
    stop_two = client.post(
        f"/trails/{trail_id}/stops", json={"site_id": second, "note": "Original note two"}
    ).json()
    assert [stop_one["stop_order"], stop_two["stop_order"]] == [1, 2]
    assert (stop_one["lat"], stop_one["lon"]) == (23.8593, 72.1018)

    reordered = client.patch(
        f"/trails/{trail_id}/stops/reorder",
        json={"stop_ids": [stop_two["id"], stop_one["id"]]},
    )
    assert reordered.status_code == 200
    assert [stop["site_id"] for stop in reordered.json()] == [second, first]

    journal = client.get(f"/trails/{trail_id}/journal").json()
    assert journal["trail_id"] == trail_id
    assert [entry["site_name"] for entry in journal["entries"]] == [
        "Adalaj Stepwell",
        "Rani ki Vav",
    ]
    assert journal["entries"][1]["original_note"] == "Original note one"
    assert journal["entries"][1]["generated_summary"] != journal["entries"][1]["original_note"]

    summary = client.get(f"/trails/{trail_id}/summary").json()
    assert summary["sites"] == 2
    assert summary["photos"] == 0
    assert summary["distance_mode"] == "straight_line"
    assert summary["missing_coordinates"] == []
    assert summary["legs"][0]["from"] == second
    assert summary["legs"][0]["to"] == first
    assert summary["total_km"] > 0


def test_trail_errors(client: TestClient):
    assert client.get("/trails/999").status_code == 404
    assert client.patch("/trails/999", json={"title": "x"}).status_code == 404
    assert client.post("/trails/999/stops", json={"site_id": 1}).status_code == 404
    assert client.delete("/trails/999/stops/1").status_code == 404
    assert client.get("/trails/999/journal").status_code == 404
    assert client.get("/trails/999/summary").status_code == 404

    trail_id = client.post("/trails", json={"title": "empty"}).json()["id"]
    assert client.post(f"/trails/{trail_id}/stops", json={"site_id": 999}).status_code == 404
    assert (
        client.patch(f"/trails/{trail_id}/stops/reorder", json={"stop_ids": [1]}).status_code == 400
    )
    assert client.patch(f"/trails/{trail_id}", json={}).status_code == 422
    assert client.post("/trails/from-images", json={"title": "empty"}).status_code == 400


def test_update_trail_and_remove_stop_renumbers(client: TestClient, clean_db, db):
    first = _site(client, "Rani ki Vav", 23.8593, 72.1018)
    second = _site(client, "Adalaj Stepwell", 23.1667, 72.5833)
    third = _site(client, "Dada Harir Stepwell", 23.0403, 72.5797)

    trail_id = client.post("/trails", json={"title": "Original"}).json()["id"]
    for site_id in (first, second, third):
        assert (
            client.post(f"/trails/{trail_id}/stops", json={"site_id": site_id}).status_code == 201
        )

    updated = client.patch(f"/trails/{trail_id}", json={"title": "Renamed", "is_public": True})
    assert updated.status_code == 200
    assert (updated.json()["title"], updated.json()["is_public"]) == ("Renamed", True)

    stops = client.get(f"/trails/{trail_id}").json()["stops"]
    removed = client.delete(f"/trails/{trail_id}/stops/{stops[1]['id']}")
    assert removed.status_code == 200
    assert [stop["stop_order"] for stop in removed.json()] == [1, 2]
    assert [stop["site_id"] for stop in removed.json()] == [first, third]
    assert client.delete(f"/trails/{trail_id}/stops/{stops[1]['id']}").status_code == 404


def test_summary_reports_missing_coordinates(client: TestClient, clean_db, db):
    located = _site(client, "Rani ki Vav", 23.8593, 72.1018)
    without_coords = client.post("/sites", json={"name": "Unlocated"}).json()["id"]

    trail_id = client.post("/trails", json={"title": "Mixed"}).json()["id"]
    client.post(f"/trails/{trail_id}/stops", json={"site_id": located})
    client.post(f"/trails/{trail_id}/stops", json={"site_id": without_coords})

    summary = client.get(f"/trails/{trail_id}/summary").json()
    assert summary["missing_coordinates"] == [without_coords]
    assert summary["legs"] == []
    assert summary["total_km"] == 0


def test_empty_trail_summary_is_straight_line(client: TestClient, clean_db, db):
    trail_id = client.post("/trails", json={"title": "Empty"}).json()["id"]
    summary = client.get(f"/trails/{trail_id}/summary").json()
    assert summary["sites"] == 0
    assert summary["distance_mode"] == "straight_line"
    assert summary["missing_coordinates"] == []
    assert summary["legs"] == []


def test_trail_from_images_orders_visits_and_reports_skipped(client: TestClient, clean_db, db):
    first = _site(client, "Rani ki Vav", 23.8593, 72.1018)
    second = _site(client, "Adalaj Stepwell", 23.1667, 72.5833)
    db.execute(
        """INSERT INTO images (site_id, storage_path, captured_at)
           VALUES (%s, '/tmp/second.jpg', '2026-11-02 10:00+00')""",
        (second,),
    )
    db.execute(
        """INSERT INTO images (site_id, storage_path, captured_at)
           VALUES (%s, '/tmp/first.jpg', '2026-11-01 09:00+00')""",
        (first,),
    )
    db.execute(
        """INSERT INTO images (site_id, storage_path, captured_at)
           VALUES (%s, '/tmp/no-time.jpg', NULL)""",
        (first,),
    )
    db.commit()

    response = client.post("/trails/from-images", json={"title": "Trip"})
    assert response.status_code == 201
    body = response.json()
    assert (body["images_used"], body["images_skipped"]) == (2, 1)
    assert [stop["site_id"] for stop in body["trail"]["stops"]] == [first, second]
    assert [stop["visit_date"] for stop in body["trail"]["stops"]] == [
        "2026-11-01",
        "2026-11-02",
    ]


def test_list_trails_filters(client: TestClient):
    client.post("/trails", json={"title": "private", "created_by": "Asha"})
    client.post("/trails", json={"title": "public", "created_by": "Ravi", "is_public": True})

    assert [trail["title"] for trail in client.get("/trails").json()] == ["public", "private"]
    assert [
        trail["title"] for trail in client.get("/trails", params={"created_by": "Asha"}).json()
    ] == ["private"]
    assert [
        trail["title"] for trail in client.get("/trails", params={"is_public": True}).json()
    ] == ["public"]
