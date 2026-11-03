from fastapi.testclient import TestClient


def test_user_creation_is_idempotent_by_email(client: TestClient):
    first = client.post("/users", json={"name": "Asha", "email": "asha@example.org"})
    second = client.post("/users", json={"name": "Asha again", "email": "asha@example.org"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["name"] == "Asha"

    assert client.get(f"/users/{first.json()['id']}").json()["role"] == "reviewer"
    assert len(client.get("/users").json()) == 1
    assert client.get("/users/999").status_code == 404


def test_user_role_validation(client: TestClient):
    assert client.post("/users", json={"name": "X", "role": "superuser"}).status_code == 422
