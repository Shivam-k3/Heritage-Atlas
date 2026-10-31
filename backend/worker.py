"""Polls the jobs table. Run: python worker.py
A failed job marks the image 'failed' but never deletes the upload or the notes."""

import time
import traceback

from app import ml
from app.db import connect


def seed_tags(conn):
    for label in ml.SITE_TYPES:
        conn.execute(
            "INSERT INTO tags(label, tag_type) VALUES (%s,'site_type') ON CONFLICT DO NOTHING",
            (label,),
        )
    for label in ml.FEATURES:
        conn.execute(
            "INSERT INTO tags(label, tag_type) VALUES (%s,'feature') ON CONFLICT DO NOTHING",
            (label,),
        )
    conn.commit()


def process(conn, job):
    img = conn.execute("SELECT * FROM images WHERE id=%s", (job["image_id"],)).fetchone()
    emb = ml.embed_image(img["storage_path"])
    conn.execute(
        "UPDATE images SET clip_embedding=%s, status='processed' WHERE id=%s", (emb, img["id"])
    )
    for label, _, score in ml.tag_image(emb):
        tag = conn.execute("SELECT id FROM tags WHERE label=%s", (label,)).fetchone()
        conn.execute(
            """INSERT INTO image_tags(image_id, tag_id, score, status)
                        VALUES (%s,%s,%s,'auto') ON CONFLICT (image_id, tag_id) DO NOTHING""",
            (img["id"], tag["id"], score),
        )
    site = conn.execute(
        "SELECT id, description FROM sites WHERE id=%s", (img["site_id"],)
    ).fetchone()
    if site["description"]:
        conn.execute(
            "UPDATE sites SET description_embedding=%s WHERE id=%s",
            (ml.embed_text(site["description"]), site["id"]),
        )


def main():
    conn = connect()
    seed_tags(conn)
    print("worker ready")
    while True:
        job = conn.execute("""UPDATE jobs SET status='running' WHERE id = (
            SELECT id FROM jobs WHERE status='pending' ORDER BY id
            FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *""").fetchone()
        conn.commit()
        if not job:
            time.sleep(2)
            continue
        try:
            process(conn, job)
            conn.execute("UPDATE jobs SET status='done' WHERE id=%s", (job["id"],))
        except Exception:
            conn.rollback()
            conn.execute(
                "UPDATE jobs SET status='failed', error=%s WHERE id=%s",
                (traceback.format_exc(), job["id"]),
            )
            conn.execute("UPDATE images SET status='failed' WHERE id=%s", (job["image_id"],))
        conn.commit()


if __name__ == "__main__":
    main()
