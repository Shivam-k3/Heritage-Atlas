import numpy as np
from app import ml
from fastapi.testclient import TestClient


def _text_vector(index: int) -> np.ndarray:
    vector = np.zeros(384, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _clip_vector(index: int) -> np.ndarray:
    vector = np.zeros(512, dtype=np.float32)
    vector[index] = 1.0
    return vector


def _seed(db, tmp_path) -> dict[str, int]:
    image_path = tmp_path / "one.png"
    image_path.write_bytes(b"x")
    first = db.execute(
        """INSERT INTO sites (name, region, category, description, description_embedding)
           VALUES ('Rani ki Vav', 'Gujarat', 'stepwell', 'carved stepwell', %s)
           RETURNING id""",
        (_text_vector(0),),
    ).fetchone()
    second = db.execute(
        """INSERT INTO sites (name, region, category, description, description_embedding)
           VALUES ('Kumbhalgarh Fort', 'Rajasthan', 'fort', 'hill fort', %s)
           RETURNING id""",
        (_text_vector(1),),
    ).fetchone()
    image = db.execute(
        """INSERT INTO images (site_id, storage_path, clip_embedding, status)
           VALUES (%s, %s, %s, 'processed') RETURNING id""",
        (first["id"], str(image_path), _clip_vector(0)),
    ).fetchone()
    second_image = db.execute(
        """INSERT INTO images (site_id, storage_path, clip_embedding, status)
           VALUES (%s, %s, %s, 'processed') RETURNING id""",
        (second["id"], str(image_path), _clip_vector(1)),
    ).fetchone()
    db.commit()
    return {
        "first": int(first["id"]),
        "second": int(second["id"]),
        "image": int(image["id"]),
        "second_image": int(second_image["id"]),
    }


def test_text_search_orders_by_description_similarity(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    monkeypatch.setattr(ml, "embed_text", lambda _: _text_vector(0))

    rows = client.get("/search/text", params={"q": "stepwell", "k": 5}).json()
    assert [row["id"] for row in rows] == [ids["first"], ids["second"]]
    assert rows[0]["score"] > rows[1]["score"]


def test_image_search_returns_public_url_and_filters(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    monkeypatch.setattr(ml, "embed_clip_text", lambda _: _clip_vector(0))

    rows = client.get("/search/images", params={"q": "carved stone", "k": 5}).json()
    assert [row["image_id"] for row in rows] == [ids["image"], ids["second_image"]]
    assert rows[0]["url"].startswith("/files/")
    assert rows[0]["score"] > rows[1]["score"]

    filtered = client.get(
        "/search/images", params={"q": "carved stone", "region": "Rajasthan"}
    ).json()
    assert [row["site_id"] for row in filtered] == [ids["second"]]


def test_search_tag_and_verified_filters(client: TestClient, clean_db, db, tmp_path, monkeypatch):
    ids = _seed(db, tmp_path)
    tag = db.execute(
        "INSERT INTO tags (label, tag_type) VALUES ('jali work', 'feature') RETURNING id"
    ).fetchone()
    db.execute(
        """INSERT INTO image_tags (image_id, tag_id, score, status)
           VALUES (%s, %s, 0.3, 'auto')""",
        (ids["image"], tag["id"]),
    )
    db.commit()
    monkeypatch.setattr(ml, "embed_clip_text", lambda _: _clip_vector(0))

    assert len(client.get("/search/images", params={"q": "x", "tag": "jali work"}).json()) == 1
    assert client.get("/search/images", params={"q": "x", "verified_only": True}).json() == []

    db.execute("UPDATE image_tags SET status='verified'")
    db.commit()
    assert len(client.get("/search/images", params={"q": "x", "verified_only": True}).json()) == 1


def test_search_requires_a_query(client: TestClient):
    assert client.get("/search/text").status_code == 422
    assert client.get("/search/images", params={"q": ""}).status_code == 422


def test_search_rejects_a_blank_query(client: TestClient):
    assert client.get("/search/text", params={"q": "   "}).status_code == 400
    assert client.get("/search/images", params={"q": "   "}).status_code == 400


def _seed_site_images(db, tmp_path, site_id: int, count: int) -> list[int]:
    path = tmp_path / "shared.png"
    path.write_bytes(b"x")
    ids = []
    for index in range(count):
        row = db.execute(
            """INSERT INTO images (site_id, storage_path, clip_embedding, status, author, licence)
               VALUES (%s, %s, %s, 'processed', 'A. Photographer', 'CC BY-SA 4.0')
               RETURNING id""",
            (site_id, str(path), _clip_vector(index % 2)),
        ).fetchone()
        ids.append(int(row["id"]))
    db.commit()
    return ids


def test_image_search_includes_active_tags_and_provenance(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    tag = db.execute(
        "INSERT INTO tags (label, tag_type) VALUES ('jali work', 'feature') RETURNING id"
    ).fetchone()
    rejected = db.execute(
        "INSERT INTO tags (label, tag_type) VALUES ('domes', 'feature') RETURNING id"
    ).fetchone()
    db.execute(
        """INSERT INTO image_tags
               (image_id, tag_id, score, status, model_name, model_version, prompt_version)
           VALUES (%s, %s, 0.31, 'verified', 'clip-ViT-B-32', 'clip-ViT-B-32', 'heritage-v2')""",
        (ids["image"], tag["id"]),
    )
    db.execute(
        """INSERT INTO image_tags (image_id, tag_id, score, status)
           VALUES (%s, %s, 0.4, 'rejected')""",
        (ids["image"], rejected["id"]),
    )
    db.commit()
    monkeypatch.setattr(ml, "embed_clip_text", lambda _: _clip_vector(0))

    rows = client.get("/search/images", params={"q": "x", "k": 1}).json()
    hit = rows[0]
    assert hit["image_id"] == ids["image"]
    assert hit["author"] == "A. Photographer"
    assert hit["licence"] == "CC BY-SA 4.0"
    assert [tag["label"] for tag in hit["tags"]] == ["jali work"]
    assert hit["tags"][0]["status"] == "verified"
    assert hit["tags"][0]["prompt_version"] == "heritage-v2"


def test_by_image_excludes_the_query_image(client: TestClient, clean_db, db, tmp_path, monkeypatch):
    ids = _seed(db, tmp_path)
    payload = b"the exact query image bytes"
    import hashlib

    db.execute(
        "UPDATE images SET sha256=%s WHERE id=%s",
        (hashlib.sha256(payload).hexdigest(), ids["image"]),
    )
    db.commit()
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))

    rows = client.post(
        "/search/by-image", files={"file": ("query.png", payload, "image/png")}
    ).json()
    assert rows
    assert ids["image"] not in [row["image_id"] for row in rows]


def test_by_image_cross_site_excludes_every_image_from_the_query_site(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    same_site = _seed_site_images(db, tmp_path, ids["first"], 2)
    payload = b"query bytes for cross site"
    import hashlib

    db.execute(
        "UPDATE images SET sha256=%s WHERE id=%s",
        (hashlib.sha256(payload).hexdigest(), same_site[0]),
    )
    db.commit()
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))

    rows = client.post(
        "/search/by-image",
        files={"file": ("query.png", payload, "image/png")},
        params={"cross_site": "true"},
    ).json()
    assert rows
    assert all(row["site_id"] != ids["first"] for row in rows)
    assert ids["second"] in [row["site_id"] for row in rows]


def test_by_image_with_unknown_site_excludes_only_the_exact_image(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))

    rows = client.post(
        "/search/by-image",
        files={"file": ("query.png", b"unseen bytes", "image/png")},
        params={"exclude_image_id": ids["image"]},
    ).json()
    assert ids["image"] not in [row["image_id"] for row in rows]
    assert [row["image_id"] for row in rows] == [ids["second_image"]]


def test_by_image_can_return_an_empty_result(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    _seed(db, tmp_path)
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))
    rows = client.post(
        "/search/by-image",
        files={"file": ("query.png", b"unseen bytes", "image/png")},
        params={"region": "Nowhere"},
    ).json()
    assert rows == []


def test_by_image_diversity_caps_one_site_per_page(
    client: TestClient, clean_db, db, tmp_path, monkeypatch
):
    ids = _seed(db, tmp_path)
    _seed_site_images(db, tmp_path, ids["first"], 3)
    _seed_site_images(db, tmp_path, ids["second"], 2)
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))

    rows = client.post(
        "/search/by-image",
        files={"file": ("query.png", b"unseen bytes", "image/png")},
        params={"k": 5, "max_per_site": 1},
    ).json()
    site_ids = [row["site_id"] for row in rows]
    assert len(site_ids) == len(set(site_ids))
    assert len(rows) == 2


def test_by_image_respects_k_and_offset(client: TestClient, clean_db, db, tmp_path, monkeypatch):
    ids = _seed(db, tmp_path)
    _seed_site_images(db, tmp_path, ids["first"], 3)
    monkeypatch.setattr(ml, "embed_image", lambda _: _clip_vector(0))

    first = client.post(
        "/search/by-image", files={"file": ("q.png", b"unseen", "image/png")}, params={"k": 2}
    ).json()
    second = client.post(
        "/search/by-image",
        files={"file": ("q.png", b"unseen", "image/png")},
        params={"k": 2, "offset": 2},
    ).json()
    assert len(first) == 2
    assert not {row["image_id"] for row in first} & {row["image_id"] for row in second}
