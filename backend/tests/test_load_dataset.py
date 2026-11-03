import hashlib
import importlib.util
from pathlib import Path

import pytest
from app import db

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "load_dataset.py"
SPEC = importlib.util.spec_from_file_location("load_dataset", MODULE_PATH)
assert SPEC and SPEC.loader
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)


def _manifest(tmp_path: Path, content: bytes = b"image") -> dict:
    image = tmp_path / "image.jpg"
    image.write_bytes(content)
    return {
        "sites": [
            {
                "name": "Test Site",
                "region": "Gujarat",
                "images": [
                    {
                        "local_path": "image.jpg",
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
        ]
    }


def test_dry_run_validates_without_opening_database(tmp_path, monkeypatch, capsys):
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(loader, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(loader, "connect", lambda: pytest.fail("database opened"))

    report = loader._dry_run(manifest)

    assert report == {
        "site_inserts": 1,
        "site_updates": 0,
        "image_inserts": 1,
        "image_skips": 0,
        "job_inserts": 1,
        "existing_images_without_jobs": "not checked (database not accessed)",
    }
    assert "database" not in capsys.readouterr().out.lower()


@pytest.mark.parametrize(
    "manifest_error",
    ["missing", "mismatch"],
)
def test_dry_run_rejects_missing_or_mismatched_image(tmp_path, manifest_error):
    manifest = _manifest(tmp_path)
    if manifest_error == "missing":
        manifest["sites"][0]["images"][0]["local_path"] = "missing.jpg"
    else:
        manifest["sites"][0]["images"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError):
        loader._dry_run(manifest)


class FakeResult:
    def __init__(self, rows=None, row=None):
        self.rows = rows or []
        self.row = row

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, existing=None, job=None):
        self.existing = existing
        self.job = job
        self.inserts = 0

    def execute(self, query, params=()):
        if "SELECT id FROM sites" in query:
            return FakeResult(rows=self.existing or [])
        if "SELECT id, status FROM images" in query:
            return FakeResult(row=self.existing)
        if "SELECT id FROM jobs" in query:
            return FakeResult(row=self.job)
        if "INSERT INTO jobs" in query:
            self.inserts += 1
            return FakeResult(row={"id": 2})
        raise AssertionError(query)


def test_duplicate_existing_site_match_is_rejected():
    conn = FakeConnection(existing=[{"id": 1}, {"id": 2}])

    with pytest.raises(ValueError, match="duplicate existing site"):
        loader._site_id(conn, {"name": "Test Site", "region": "Gujarat"})


def test_existing_image_with_job_does_not_create_duplicate():
    conn = FakeConnection(existing={"id": 1, "status": "uploaded"}, job={"id": 4})

    assert loader._insert_image(conn, 1, {"sha256": "a" * 64}, True) is False
    assert conn.inserts == 0


def test_existing_eligible_image_without_job_receives_one():
    conn = FakeConnection(existing={"id": 1, "status": "uploaded"})

    assert loader._insert_image(conn, 1, {"sha256": "a" * 64}, True) is False
    assert conn.inserts == 1


def test_connect_rolls_back_on_failure(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.rolled_back = False
            self.committed = False

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

    fake = FakeConnection()
    monkeypatch.setattr(db, "open_connection", lambda: fake)

    with pytest.raises(RuntimeError):
        with db.connect():
            raise RuntimeError("loader failure")

    assert fake.rolled_back is True
    assert fake.committed is False
