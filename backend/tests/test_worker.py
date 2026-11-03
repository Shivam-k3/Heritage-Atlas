from datetime import UTC, datetime, timedelta

import numpy as np
import psycopg
import worker as worker_module
from app import config
from psycopg.rows import dict_row


def _seed_image(
    db, tmp_path, job_status: str = "pending", claimed_at: datetime | None = None
) -> tuple[int, int]:
    path = tmp_path / "photo.png"
    path.write_bytes(b"not read by the fake model")
    site = db.execute(
        "INSERT INTO sites (name, description) VALUES ('Rani ki Vav', 'A stepwell') RETURNING id"
    ).fetchone()
    image = db.execute(
        """INSERT INTO images (site_id, storage_path, status)
           VALUES (%s, %s, 'uploaded') RETURNING id""",
        (site["id"], str(path)),
    ).fetchone()
    job = db.execute(
        """INSERT INTO jobs (image_id, status, claimed_at)
           VALUES (%s, %s, %s) RETURNING id""",
        (image["id"], job_status, claimed_at),
    ).fetchone()
    db.commit()
    return int(image["id"]), int(job["id"])


def test_process_image_is_idempotent_and_preserves_human_tags(clean_db, db, tmp_path, monkeypatch):
    image_id, _ = _seed_image(db, tmp_path)
    worker_module.seed_tags(db)
    monkeypatch.setattr(worker_module.ml, "embed_image", lambda _: np.eye(512, dtype=np.float32)[0])
    monkeypatch.setattr(worker_module.ml, "embed_text", lambda _: np.zeros(384, dtype=np.float32))
    monkeypatch.setattr(
        worker_module.ml,
        "tag_image",
        lambda _: [("jali work", "feature", 0.31), ("domes", "feature", 0.24)],
    )

    assert worker_module.process_image(db, image_id) == 2
    db.commit()
    first = db.execute(
        """SELECT t.label, it.status, it.score FROM image_tags it
           JOIN tags t ON t.id=it.tag_id WHERE it.image_id=%s ORDER BY t.label""",
        (image_id,),
    ).fetchall()
    assert [(row["label"], row["status"]) for row in first] == [
        ("domes", "auto"),
        ("jali work", "auto"),
    ]

    db.execute(
        """UPDATE image_tags SET status='verified'
           WHERE image_id=%s AND tag_id=(SELECT id FROM tags WHERE label='jali work')""",
        (image_id,),
    )
    db.commit()

    monkeypatch.setattr(worker_module.ml, "tag_image", lambda _: [("domes", "feature", 0.5)])
    assert worker_module.process_image(db, image_id) == 1
    db.commit()
    second = db.execute(
        """SELECT t.label, it.status FROM image_tags it
           JOIN tags t ON t.id=it.tag_id WHERE it.image_id=%s ORDER BY t.label""",
        (image_id,),
    ).fetchall()
    assert [(row["label"], row["status"]) for row in second] == [
        ("domes", "auto"),
        ("jali work", "verified"),
    ]

    status = db.execute("SELECT status FROM images WHERE id=%s", (image_id,)).fetchone()
    assert status["status"] == "processed"


def test_fail_retries_then_marks_image_failed(clean_db, db, tmp_path, monkeypatch):
    image_id, job_id = _seed_image(db, tmp_path, job_status="running", claimed_at=datetime.now(UTC))
    monkeypatch.setattr(config, "job_max_retries", lambda: 2)
    job = db.execute("SELECT id, image_id, retry_count FROM jobs WHERE id=%s", (job_id,)).fetchone()

    worker_module._fail(db, job, "first failure")
    job = db.execute("SELECT id, image_id, retry_count FROM jobs WHERE id=%s", (job_id,)).fetchone()
    assert job["retry_count"] == 1
    assert (
        db.execute("SELECT status FROM jobs WHERE id=%s", (job_id,)).fetchone()["status"]
        == "pending"
    )

    worker_module._fail(db, job, "second failure")
    assert (
        db.execute("SELECT status FROM jobs WHERE id=%s", (job_id,)).fetchone()["status"]
        == "failed"
    )
    assert (
        db.execute("SELECT status FROM images WHERE id=%s", (image_id,)).fetchone()["status"]
        == "failed"
    )


def test_stale_running_job_is_recovered_and_processed(clean_db, db, tmp_path, monkeypatch):
    image_id, job_id = _seed_image(
        db, tmp_path, job_status="running", claimed_at=datetime.now(UTC) - timedelta(minutes=10)
    )
    monkeypatch.setattr(config, "job_lease_seconds", lambda: 60)
    worker_module.seed_tags(db)
    monkeypatch.setattr(worker_module.ml, "embed_image", lambda _: np.eye(512, dtype=np.float32)[0])
    monkeypatch.setattr(worker_module.ml, "embed_text", lambda _: np.zeros(384, dtype=np.float32))
    monkeypatch.setattr(worker_module.ml, "tag_image", lambda _: [])

    assert worker_module.recover_stale(db) == 1
    job = worker_module._claim(db, "test-worker")
    assert job is not None and int(job["id"]) == job_id
    assert job["worker_id"] == "test-worker"
    assert worker_module.process_image(db, int(job["image_id"])) == 0
    db.execute(
        "UPDATE jobs SET status='done', claimed_at=NULL, worker_id=NULL WHERE id=%s", (job_id,)
    )
    db.commit()
    assert (
        db.execute("SELECT status FROM jobs WHERE id=%s", (job_id,)).fetchone()["status"] == "done"
    )
    assert image_id


def test_running_job_inside_its_lease_is_not_recovered(clean_db, db, tmp_path, monkeypatch):
    _, job_id = _seed_image(db, tmp_path, job_status="running", claimed_at=datetime.now(UTC))
    monkeypatch.setattr(config, "job_lease_seconds", lambda: 3600)
    assert worker_module.recover_stale(db) == 0
    assert (
        db.execute("SELECT status FROM jobs WHERE id=%s", (job_id,)).fetchone()["status"]
        == "running"
    )


def test_retry_backoff_blocks_immediate_reclaim(clean_db, db, tmp_path, monkeypatch):
    _, job_id = _seed_image(db, tmp_path, job_status="running", claimed_at=datetime.now(UTC))
    monkeypatch.setattr(config, "job_max_retries", lambda: 3)
    monkeypatch.setattr(config, "job_retry_backoff_seconds", lambda: 60)
    job = db.execute("SELECT id, image_id, retry_count FROM jobs WHERE id=%s", (job_id,)).fetchone()

    worker_module._fail(db, job, "transient")
    assert worker_module._claim(db, "test-worker") is None

    db.execute("UPDATE jobs SET available_at=now() WHERE id=%s", (job_id,))
    db.commit()
    claimed = worker_module._claim(db, "test-worker")
    assert claimed is not None and int(claimed["id"]) == job_id


def test_two_workers_claim_different_jobs(clean_db, db, tmp_path, database):
    _, first_job = _seed_image(db, tmp_path)
    _, second_job = _seed_image(db, tmp_path)

    with psycopg.connect(database, row_factory=dict_row) as other:
        claimed_first = worker_module._claim(db, "worker-a")
        claimed_second = worker_module._claim(other, "worker-b")

    assert claimed_first is not None and claimed_second is not None
    assert {int(claimed_first["id"]), int(claimed_second["id"])} == {first_job, second_job}


def test_claim_skips_jobs_with_a_future_available_at(clean_db, db, tmp_path):
    _, job_id = _seed_image(db, tmp_path)
    db.execute("UPDATE jobs SET available_at=now() + interval '1 hour' WHERE id=%s", (job_id,))
    db.commit()
    assert worker_module._claim(db, "test-worker") is None


def test_stale_job_at_the_retry_limit_fails_terminally(clean_db, db, tmp_path, monkeypatch):
    image_id, job_id = _seed_image(
        db, tmp_path, job_status="running", claimed_at=datetime.now(UTC) - timedelta(minutes=10)
    )
    db.execute("UPDATE jobs SET retry_count=1 WHERE id=%s", (job_id,))
    db.commit()
    monkeypatch.setattr(config, "job_lease_seconds", lambda: 60)
    monkeypatch.setattr(config, "job_max_retries", lambda: 2)

    assert worker_module.recover_stale(db) == 0
    job = db.execute("SELECT status, retry_count FROM jobs WHERE id=%s", (job_id,)).fetchone()
    assert job["status"] == "failed"
    assert job["retry_count"] == 2
    image = db.execute("SELECT status FROM images WHERE id=%s", (image_id,)).fetchone()
    assert image["status"] == "failed"


def test_rejected_tag_is_not_silently_recreated(clean_db, db, tmp_path, monkeypatch):
    image_id, _ = _seed_image(db, tmp_path)
    worker_module.seed_tags(db)
    monkeypatch.setattr(worker_module.ml, "embed_image", lambda _: np.eye(512, dtype=np.float32)[0])
    monkeypatch.setattr(worker_module.ml, "embed_text", lambda _: np.zeros(384, dtype=np.float32))
    monkeypatch.setattr(worker_module.ml, "tag_image", lambda _: [("domes", "feature", 0.4)])
    worker_module.process_image(db, image_id)
    db.execute("UPDATE image_tags SET status='rejected' WHERE image_id=%s", (image_id,))
    db.commit()

    worker_module.process_image(db, image_id)
    db.commit()
    rows = db.execute(
        "SELECT status FROM image_tags WHERE image_id=%s AND tag_id=(SELECT id FROM tags WHERE label='domes')",
        (image_id,),
    ).fetchall()
    assert [row["status"] for row in rows] == ["rejected"]
