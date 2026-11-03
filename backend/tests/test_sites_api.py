from fastapi.testclient import TestClient


def _create_site(client: TestClient, name: str = "Rani ki Vav", **overrides) -> dict:
    payload = {
        "name": name,
        "region": "Gujarat",
        "district": "Patan",
        "category": "stepwell",
        "lat": 23.8593,
        "lon": 72.1018,
        "description": "Original field note about a stepwell.",
    }
    payload.update(overrides)
    response = client.post("/sites", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_get_and_update_site(client: TestClient):
    site = _create_site(client)
    assert site["name"] == "Rani ki Vav"
    assert site["images"] == []

    response = client.get(f"/sites/{site['id']}")
    assert response.status_code == 200
    assert response.json()["description"] == "Original field note about a stepwell."

    response = client.patch(f"/sites/{site['id']}", json={"description": "Corrected note"})
    assert response.status_code == 200
    assert response.json()["description"] == "Corrected note"

    assert client.get("/sites/9999").status_code == 404
    assert client.patch("/sites/9999", json={"name": "x"}).status_code == 404


def test_list_sites_returns_bare_array_and_filters(client: TestClient):
    _create_site(client)
    _create_site(
        client, "Kumbhalgarh Fort", region="Rajasthan", category="fort", lat=25.15, lon=73.58
    )

    all_sites = client.get("/sites").json()
    assert isinstance(all_sites, list)
    assert len(all_sites) == 2

    gujarat = client.get("/sites", params={"region": "Gujarat"}).json()
    assert [site["name"] for site in gujarat] == ["Rani ki Vav"]

    forts = client.get("/sites", params={"category": "fort"}).json()
    assert [site["name"] for site in forts] == ["Kumbhalgarh Fort"]

    page = client.get("/sites", params={"limit": 1, "offset": 1}).json()
    assert len(page) == 1


def test_update_requires_at_least_one_field(client: TestClient):
    site = _create_site(client)
    assert client.patch(f"/sites/{site['id']}", json={}).status_code == 422
    assert client.patch(f"/sites/{site['id']}", json={"unknown": 1}).status_code == 422


def test_invalid_coordinates_are_rejected(client: TestClient):
    response = client.post("/sites", json={"name": "bad", "lat": 99})
    assert response.status_code == 422
