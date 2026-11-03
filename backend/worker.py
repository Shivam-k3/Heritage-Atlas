"""Database-backed worker. Run: python worker.py

Claims one job at a time with FOR UPDATE SKIP LOCKED. A failed job is retried up to
JOB_MAX_RETRIES attempts with exponential backoff; a running job older than
JOB_LEASE_SECONDS is assumed abandoned and returned to the queue. The original upload and
notes are never deleted. Re-running a job replaces only auto tags, so human decisions survive.
"""

import argparse
import logging
import time
import traceback

from app import config, ml
from app.db import open_connection

logger = logging.getLogger("heritage_atlas.worker")
logging.basicConfig(level=logging.INFO)


def seed_tags(conn) -> None:
    for label in ml.FEATURES:
        conn.execute(
            "INSERT INTO tags(label, tag_type) VALUES (%s, 'feature') ON CONFLICT DO NOTHING",
            (label,),
        )
    conn.commit()


def process_image(conn, image_id: int) -> int:
    image = conn.execute(
        "SELECT id, site_id, storage_path, status FROM images WHERE id=%s", (image_id,)
    ).fetchone()
    if not image:
        raise RuntimeError(f"image {image_id} does not exist")
    conn.execute("UPDATE images SET status='processing', updated_at=now() WHERE id=%s", (image_id,))

    embedding = ml.embed_image(image["storage_path"])
    conn.execute(
        "UPDATE images SET clip_embedding=%s, status='processed', updated_at=now() WHERE id=%s",
        (embedding, image_id),
    )

    info = ml.model_info()
    suggestions = ml.tag_image(embedding)
    conn.execute("DELETE FROM image_tags WHERE image_id=%s AND status='auto'", (image_id,))
    for label, tag_type, score in suggestions:
        tag = conn.execute(
            """INSERT INTO tags(label, tag_type) VALUES (%s, %s)
               ON CONFLICT (label) DO UPDATE SET label=EXCLUDED.label
               RETURNING id""",
            (label, tag_type),
        ).fetchone()
        conn.execute(
            """INSERT INTO image_tags
                   (image_id, tag_id, score, status, model_name, model_version, prompt_version)
               VALUES (%s, %s, %s, 'auto', %s, %s, %s)
               ON CONFLICT (image_id, tag_id) DO UPDATE SET
                   score=EXCLUDED.score,
                   model_name=EXCLUDED.model_name,
                   model_version=EXCLUDED.model_version,
                   prompt_version=EXCLUDED.prompt_version
               WHERE image_tags.status='auto'""",
            (
                image_id,
                tag["id"],
                score,
                info["clip_model"],
                info["clip_model"],
                info["prompt_version"],
            ),
        )

    site = conn.execute(
        "SELECT id, description FROM sites WHERE id=%s", (image["site_id"],)
    ).fetchone()
    if site and site["description"]:
        conn.execute(
            "UPDATE sites SET description_embedding=%s, updated_at=now() WHERE id=%s",
            (ml.embed_text(site["description"]), site["id"]),
        )
    return len(suggestions)


def recover_stale(conn, lease_seconds: int | None = None) -> int:
    """Return abandoned running jobs to the queue. Safe to call while other workers run.

    A stale claim counts as an attempt: otherwise a job that kills its worker every time
    would be retried forever. Jobs at the configured retry limit fail terminally instead.
    """
    lease = config.job_lease_seconds() if lease_seconds is None else lease_seconds
    rows = conn.execute(
        """SELECT id, image_id, retry_count FROM jobs
            WHERE status='running'
              AND (claimed_at IS NULL OR claimed_at < now() - (%s * interval '1 second'))
            FOR UPDATE SKIP LOCKED""",
        (lease,),
    ).fetchall()
    recovered = 0
    for row in rows:
        retries = int(row["retry_count"]) + 1
        if retries >= config.job_max_retries():
            conn.execute(
                """UPDATE jobs SET status='failed', retry_count=%s, error=%s,
                                  claimed_at=NULL, worker_id=NULL, updated_at=now()
                   WHERE id=%s""",
                (retries, "worker stopped before the job finished", row["id"]),
            )
            conn.execute(
                "UPDATE images SET status='failed', updated_at=now() WHERE id=%s",
                (row["image_id"],),
            )
        else:
            conn.execute(
                """UPDATE jobs SET status='pending', retry_count=%s, claimed_at=NULL,
                                  worker_id=NULL, updated_at=now()
                   WHERE id=%s""",
                (retries, row["id"]),
            )
            recovered += 1
    conn.commit()
    if rows:
        logger.warning("recovered %s stale job(s), %s exhausted", len(rows), len(rows) - recovered)
    return recovered


def _claim(conn, worker_id: str | None = None):
    job = conn.execute(
        """UPDATE jobs
              SET status='running', claimed_at=now(), worker_id=%s, updated_at=now()
            WHERE id = (SELECT id FROM jobs
                        WHERE status='pending' AND available_at <= now()
                        ORDER BY available_at, id
                        FOR UPDATE SKIP LOCKED LIMIT 1)
            RETURNING id, image_id, retry_count, worker_id""",
        (worker_id or config.worker_id(),),
    ).fetchone()
    conn.commit()
    return job


def _fail(conn, job, error: str) -> None:
    retries = int(job["retry_count"]) + 1
    terminal = retries >= config.job_max_retries()
    if terminal:
        conn.execute(
            """UPDATE jobs SET status='failed', error=%s, retry_count=%s,
                              claimed_at=NULL, worker_id=NULL, updated_at=now()
               WHERE id=%s""",
            (error[:4000], retries, job["id"]),
        )
        conn.execute(
            "UPDATE images SET status='failed', updated_at=now() WHERE id=%s", (job["image_id"],)
        )
    else:
        backoff = min(config.job_retry_backoff_seconds() * (2 ** (retries - 1)), 3600)
        conn.execute(
            """UPDATE jobs SET status='pending', error=%s, retry_count=%s,
                              claimed_at=NULL, worker_id=NULL,
                              available_at=now() + (%s * interval '1 second'),
                              updated_at=now()
               WHERE id=%s""",
            (error[:4000], retries, backoff, job["id"]),
        )
    conn.commit()


def main(drain: bool = False) -> None:
    conn = open_connection()
    seed_tags(conn)
    logger.info("worker ready: %s", config.worker_id())
    while True:
        try:
            recover_stale(conn)
            job = _claim(conn)
            if not job:
                if drain:
                    logger.info("queue empty")
                    return
                time.sleep(2)
                continue
            try:
                count = process_image(conn, int(job["image_id"]))
                conn.execute(
                    """UPDATE jobs SET status='done', error=NULL, claimed_at=NULL,
                                      worker_id=NULL, available_at=now(), updated_at=now()
                       WHERE id=%s""",
                    (job["id"],),
                )
                conn.commit()
                logger.info("job %s done: image %s, %s tags", job["id"], job["image_id"], count)
            except Exception as exc:  # noqa: BLE001 - one bad image must not kill the worker
                conn.rollback()
                _fail(conn, job, f"{exc}\n{traceback.format_exc()}")
                logger.exception("job %s failed", job["id"])
        except KeyboardInterrupt:
            logger.info("worker stopped")
            return
        except Exception:  # noqa: BLE001 - reconnect after a dropped database connection
            logger.exception("worker loop error")
            try:
                conn.close()
            except Exception:  # noqa: BLE001 - the connection is already unusable
                logger.debug("closing dead connection failed", exc_info=True)
            time.sleep(2)
            conn = open_connection()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="process currently available jobs, then exit"
    )
    args = parser.parse_args()
    main(drain=args.once)
