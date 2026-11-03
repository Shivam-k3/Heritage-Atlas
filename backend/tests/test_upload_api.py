from conftest import png_bytes
from fastapi.testclient import TestClient


def test_upload_creates_site_image_and_job(client: TestClient):
    response = client.post(
        "/images/upload",
        files={"file": ("photo.png", png_bytes(), "image/png")},
        data={
            "site_name": "Rani ki Vav",
            "region": "Gujarat",
            "category": "stepwell",
            "lat": "23.8593",
            "lon": "72.1018",
            "description": "Original note",
            "author": "A. Photographer",
            "licence": "CC BY-SA 4.0",
            "source_url": "https://example.org/photo",
        },
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["duplicate"] is False
    assert body["status"] == "queued"
    assert body["url"].startswith("/files/")

    image = client.get(f"/images/{body['image_id']}").json()
    assert image["author"] == "A. Photographer"
    assert image["licence"] == "CC BY-SA 4.0"
    assert image["site_name"] == "Rani ki Vav"
    assert image["status"] == "uploaded"
    assert image["tags"] == []

    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "pending"
    assert job["image_id"] == body["image_id"]


def test_duplicate_upload_reuses_image(client: TestClient):
    data = png_bytes()
    first = client.post(
        "/images/upload",
        files={"file": ("a.png", data, "image/png")},
        data={"site_name": "Adalaj Stepwell"},
    ).json()
    second = client.post(
        "/images/upload",
        files={"file": ("b.png", data, "image/png")},
        data={"site_name": "Adalaj Stepwell"},
    )
    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    assert second.json()["image_id"] == first["image_id"]


def test_upload_validation_errors(client: TestClient):
    missing_site = client.post(
        "/images/upload", files={"file": ("a.png", png_bytes(), "image/png")}
    )
    assert missing_site.status_code == 400

    bad_file = client.post(
        "/images/upload",
        files={"file": ("a.txt", b"not an image", "text/plain")},
        data={"site_name": "X"},
    )
    assert bad_file.status_code == 400

    missing_site_id = client.post(
        "/images/upload",
        files={"file": ("a.png", png_bytes(), "image/png")},
        data={"site_id": "999"},
    )
    assert missing_site_id.status_code == 404


def test_reprocess_missing_image_is_404(client: TestClient):
    assert client.post("/images/999/reprocess").status_code == 404
    assert client.get("/images/999").status_code == 404


def test_batch_upload_accepts_mixed_files(client: TestClient):
    first = png_bytes("red")
    response = client.post(
        "/images/upload-batch",
        files=[
            ("files", ("a.png", first, "image/png")),
            ("files", ("b.png", png_bytes("blue"), "image/png")),
            ("files", ("broken.png", b"not an image", "image/png")),
            ("files", ("dupe.png", first, "image/png")),
        ],
        data={"site_name": "Rani ki Vav", "author": "A. Photographer"},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert (body["accepted"], body["duplicates"], body["rejected"]) == (2, 1, 1)
    assert body["errors"][0]["filename"] == "broken.png"
    assert len(body["results"]) == 3

    image_id = body["results"][0]["image_id"]
    assert client.get(f"/images/{image_id}").json()["author"] == "A. Photographer"


def test_batch_upload_requires_a_site_and_at_least_one_file(client: TestClient):
    no_site = client.post(
        "/images/upload-batch",
        files=[("files", ("a.png", png_bytes(), "image/png"))],
    )
    assert no_site.status_code == 400
    assert client.post("/images/upload-batch", data={"site_name": "X"}).status_code == 422
