import pytest
from app.schemas import HumanTagCreate
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_human_tag_label_must_not_be_blank():
    with pytest.raises(ValidationError):
        HumanTagCreate(image_id=1, label="   ")


def _seed_tag(db) -> dict[str, int]:
    site = db.execute("INSERT INTO sites (name) VALUES ('Rani ki Vav') RETURNING id").fetchone()
    image = db.execute(
        """INSERT INTO images (site_id, storage_path, status)
           VALUES (%s, '/tmp/x.png', 'processed') RETURNING id""",
        (site["id"],),
    ).fetchone()
    tag = db.execute(
        "INSERT INTO tags (label, tag_type) VALUES ('jali work', 'feature') RETURNING id"
    ).fetchone()
    image_tag = db.execute(
        """INSERT INTO image_tags (image_id, tag_id, score, status)
           VALUES (%s, %s, 0.21, 'auto') RETURNING id""",
        (image["id"], tag["id"]),
    ).fetchone()
    db.commit()
    return {
        "site": int(site["id"]),
        "image": int(image["id"]),
        "tag": int(tag["id"]),
        "image_tag": int(image_tag["id"]),
    }


def test_queue_lowest_score_first(client: TestClient, clean_db, db):
    ids = _seed_tag(db)
    queue = client.get("/review/queue").json()
    assert [row["id"] for row in queue] == [ids["image_tag"]]
    assert queue[0]["site_name"] == "Rani ki Vav"
    assert queue[0]["status"] == "auto"
    assert queue[0]["url"] == "/files/x.png"
    assert queue[0]["label"] == "jali work"
    assert queue[0]["score"] == 0.21

    assert client.get("/review/queue", params={"status": "nope"}).status_code == 400
    assert client.get("/review/reviewers").json() == ["asha", "ravi", "guest"]


def test_confirm_reject_and_history_are_append_only(client: TestClient, clean_db, db):
    ids = _seed_tag(db)
    confirmed = client.post(
        f"/review/tags/{ids['image_tag']}", json={"action": "confirm", "reviewer": "Asha"}
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "verified"

    rejected = client.post(
        f"/review/tags/{ids['image_tag']}", json={"action": "reject", "reviewer": "Ravi"}
    )
    assert rejected.json()["previous_status"] == "verified"
    assert rejected.json()["status"] == "rejected"

    history = client.get(f"/review/history/{ids['image_tag']}").json()
    assert [row["action"] for row in history] == ["confirm", "reject"]
    assert [row["reviewer"] for row in history] == ["asha", "ravi"]
    assert client.get("/review/history/9999").status_code == 404

    unknown = client.post(
        f"/review/tags/{ids['image_tag']}", json={"action": "confirm", "reviewer": "stranger"}
    )
    assert unknown.status_code == 400


def test_add_human_tag_is_idempotent(client: TestClient, clean_db, db):
    ids = _seed_tag(db)
    body = {"image_id": ids["image"], "label": "Domes", "reviewer": "Asha"}
    first = client.post("/review/tags/add", json=body)
    second = client.post("/review/tags/add", json=body)
    assert first.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["status"] == "added_by_human"

    tags = client.get(f"/images/{ids['image']}/tags").json()
    labels = {tag["label"]: tag for tag in tags}
    assert labels["domes"]["status"] == "added_by_human"
    assert labels["domes"]["score"] is None

    assert client.post("/review/tags/add", json={**body, "image_id": 9999}).status_code == 404
    assert (
        client.post("/review/tags/9999", json={"action": "confirm", "reviewer": "asha"}).status_code
        == 404
    )
