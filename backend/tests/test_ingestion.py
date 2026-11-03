import importlib.util
import json
from pathlib import Path

from app.services.ingestion import cluster_points, scan_folder
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _jpeg(path: Path, color: str, gps: tuple[float, float] | None = None) -> None:
    exif = Image.Exif()
    exif[36867] = "2024:01:02 03:04:05"
    if gps:
        lat, lon = gps
        exif[34853] = {
            1: "N" if lat >= 0 else "S",
            2: (abs(lat), 0, 0),
            3: "E" if lon >= 0 else "W",
            4: (abs(lon), 0, 0),
        }
    Image.new("RGB", (32, 32), color).save(path, exif=exif)


def test_scan_folder_is_recursive_and_filters_extensions(tmp_path: Path):
    (tmp_path / "nested").mkdir()
    _jpeg(tmp_path / "a.jpg", "red")
    _jpeg(tmp_path / "nested" / "b.JPG", "blue")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    entries = scan_folder(tmp_path)
    assert [entry.relative_path for entry in entries] == ["a.jpg", "nested/b.JPG"]


def test_cluster_points_uses_haversine_and_configurable_radius():
    points = [
        (10, 26.9000, 75.8000),
        (11, 26.9005, 75.8000),  # about 55 m away
        (12, 26.9100, 75.8000),  # about 1.1 km away
    ]
    clusters = cluster_points(points, radius_m=300)
    assert [cluster.image_ids for cluster in clusters] == [(10, 11), (12,)]

    wider = cluster_points(points, radius_m=2000)
    assert [cluster.image_ids for cluster in wider] == [(10, 11, 12)]
    assert wider[0].lat == round((26.9 + 26.9005 + 26.91) / 3, 7)


def test_cluster_points_rejects_invalid_radius():
    try:
        cluster_points([], radius_m=0)
    except ValueError as exc:
        assert "radius" in str(exc)
    else:
        raise AssertionError("radius_m=0 should be rejected")


def test_folder_ingestion_is_resumable_and_tolerates_bad_files(
    client, clean_db, db, tmp_path, monkeypatch
):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    folder = tmp_path / "trip"
    folder.mkdir()
    _jpeg(folder / "a.jpg", "red", gps=(26.9000, 75.8000))
    _jpeg(folder / "b.jpg", "blue", gps=(26.9005, 75.8000))
    _jpeg(folder / "c.jpg", "green", gps=(26.9100, 75.8000))
    _jpeg(folder / "d.jpg", "yellow")
    (folder / "bad.jpg").write_bytes(b"not an image")
    (folder / "duplicate.jpg").write_bytes((folder / "a.jpg").read_bytes())

    module = _load_script("ingest_folder")
    batch = module.ingest_folder(folder, radius_m=300, author="A. Photographer")

    assert batch["status"] == "completed"
    assert (batch["total_files"], batch["accepted"], batch["duplicates"], batch["rejected"]) == (
        6,
        4,
        1,
        1,
    )
    assert batch["gps_images"] == 3
    assert batch["clusters"] == 2
    statuses = [entry["status"] for entry in batch["report"]["files"]]
    assert statuses.count("accepted") == 4
    assert statuses.count("duplicate") == 1
    assert statuses.count("rejected") == 1
    assert all("storage_path" not in json.dumps(entry) for entry in batch["report"]["files"])

    images = db.execute(
        "SELECT id, site_id, captured_at, author FROM images ORDER BY id"
    ).fetchall()
    assert len(images) == 4
    assert all(row["captured_at"] is not None for row in images)
    assert all(row["author"] == "A. Photographer" for row in images)
    jobs = db.execute("SELECT status FROM jobs").fetchall()
    assert len(jobs) == 4 and all(row["status"] == "pending" for row in jobs)

    drafts = client.get("/sites/drafts").json()
    assert len(drafts) == 3  # two GPS clusters plus the no-GPS bucket
    assert all(site["status"] == "draft" for site in drafts)
    assert all(site["image_ids"] for site in drafts)
    assert sum(site["images"] for site in drafts) == 4

    batches = client.get("/ingest/batches").json()
    assert batches[0]["id"] == batch["id"]
    assert client.get(f"/ingest/batches/{batch['id']}").json()["accepted"] == 4
    assert client.get("/ingest/batches/9999").status_code == 404

    second = module.ingest_folder(folder, radius_m=300)
    assert (second["accepted"], second["duplicates"], second["rejected"]) == (0, 4, 1)
    assert db.execute("SELECT count(*) AS n FROM images").fetchone()["n"] == 4
    assert db.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 4


def test_dry_run_clusters_real_exif_without_database(tmp_path: Path):
    folder = tmp_path / "trip"
    folder.mkdir()
    _jpeg(folder / "a.jpg", "red", gps=(26.9000, 75.8000))
    _jpeg(folder / "b.jpg", "blue", gps=(26.9005, 75.8000))
    _jpeg(folder / "c.jpg", "green", gps=(26.9100, 75.8000))
    _jpeg(folder / "no-gps.jpg", "yellow")
    (folder / "duplicate.jpg").write_bytes((folder / "a.jpg").read_bytes())
    (folder / "lost.jpg").write_bytes(b"not an image")

    report = _load_script("ingest_folder").dry_run(folder, radius_m=300)
    assert report["total_files"] == 6
    assert (report["accepted"], report["duplicates"], report["rejected"]) == (4, 1, 1)
    assert report["gps_images"] == 3
    assert report["clusters"] == 2
    assert sorted(report["cluster_sizes"]) == [1, 2]


def test_draft_clusters_can_be_confirmed_rejected_and_merged(
    client, clean_db, db, tmp_path, monkeypatch
):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    folder = tmp_path / "trip"
    folder.mkdir()
    _jpeg(folder / "a.jpg", "red", gps=(26.9000, 75.8000))
    _jpeg(folder / "b.jpg", "blue", gps=(26.9100, 75.8000))
    _jpeg(folder / "c.jpg", "green", gps=(26.9200, 75.8000))
    _load_script("ingest_folder").ingest_folder(folder)

    drafts = client.get("/sites/drafts").json()
    first, second, third = (draft["id"] for draft in drafts)

    confirmed = client.post(f"/sites/{first}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "canonical"
    assert client.post(f"/sites/{first}/confirm").status_code == 400

    rejected = client.post(f"/sites/{second}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    target = client.post("/sites", json={"name": "Verified Fort", "region": "Rajasthan"}).json()
    assert client.post(f"/sites/{third}/merge", json={"target_site_id": 9999}).status_code == 404

    merged = client.post(f"/sites/{third}/merge", json={"target_site_id": target["id"]})
    assert merged.status_code == 200
    assert merged.json()["id"] == target["id"]
    assert len(merged.json()["images"]) == 1
    assert client.get("/sites/drafts").json() == []
    assert client.get(f"/sites/{third}").json()["status"] == "merged"
