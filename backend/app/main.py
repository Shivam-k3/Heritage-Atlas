import os
import shutil
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ml
from .db import UPLOAD_DIR, connect

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = FastAPI(title="Heritage Atlas API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")


def _save(upload: UploadFile) -> str:
    ext = os.path.splitext(upload.filename or "")[1] or ".jpg"
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


@app.post("/images/upload")
def upload_image(
    file: UploadFile = File(...),
    site_id: int | None = Form(None),
    site_name: str | None = Form(None),
    region: str | None = Form(None),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    description: str | None = Form(None),
    author: str | None = Form(None),
    licence: str | None = Form(None),
    source_url: str | None = Form(None),
):
    path = _save(file)
    with connect() as conn:
        if site_id is None:
            if not site_name:
                raise HTTPException(400, "site_id or site_name required")
            site_id = conn.execute(
                "INSERT INTO sites(name, region, lat, lon, description) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (site_name, region, lat, lon, description),
            ).fetchone()["id"]
        img = conn.execute(
            """INSERT INTO images(site_id, storage_path, author, licence, source_url)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (site_id, path, author, licence, source_url),
        ).fetchone()
        job = conn.execute(
            "INSERT INTO jobs(image_id) VALUES (%s) RETURNING id", (img["id"],)
        ).fetchone()
    return {"site_id": site_id, "image_id": img["id"], "job_id": job["id"], "status": "queued"}


@app.get("/jobs/{job_id}")
def job_status(job_id: int):
    with connect() as conn:
        row = conn.execute("SELECT id, status, error FROM jobs WHERE id=%s", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404)
    return row


@app.get("/sites")
def list_sites(region: str | None = None):
    with connect() as conn:
        return conn.execute(
            "SELECT id, name, region, category, lat, lon FROM sites "
            "WHERE (%s::text IS NULL OR region=%s) ORDER BY id",
            (region, region),
        ).fetchall()


@app.get("/sites/{site_id}")
def site_detail(site_id: int):
    with connect() as conn:
        site = conn.execute(
            "SELECT id, name, region, category, lat, lon, description FROM sites WHERE id=%s",
            (site_id,),
        ).fetchone()
        if not site:
            raise HTTPException(404)
        images = conn.execute(
            "SELECT id, storage_path, author, licence, source_url, status FROM images WHERE site_id=%s",
            (site_id,),
        ).fetchall()
        for im in images:
            im["url"] = "/files/" + os.path.basename(im.pop("storage_path"))
            im["tags"] = conn.execute(
                """SELECT it.id, t.label, t.tag_type, it.score, it.status FROM image_tags it
                   JOIN tags t ON t.id=it.tag_id WHERE it.image_id=%s ORDER BY it.score DESC NULLS LAST""",
                (im["id"],),
            ).fetchall()
    return {**site, "images": images}


_IMG_SQL = """SELECT i.id AS image_id, s.id AS site_id, s.name, s.region, i.storage_path,
              1 - (i.clip_embedding <=> %s) AS score
              FROM images i JOIN sites s ON s.id=i.site_id
              WHERE i.clip_embedding IS NOT NULL ORDER BY i.clip_embedding <=> %s LIMIT %s"""


def _image_results(emb, k):
    with connect() as conn:
        rows = conn.execute(_IMG_SQL, (emb, emb, k)).fetchall()
    for r in rows:
        r["url"] = "/files/" + os.path.basename(r.pop("storage_path"))
    return rows


@app.get("/search/images")  # CLIP text -> image
def search_text_to_image(q: str, k: int = 10):
    return _image_results(ml.embed_clip_text(q), k)


@app.post("/search/by-image")  # CLIP image -> image
def search_by_image(file: UploadFile = File(...), k: int = 10):
    return _image_results(ml.embed_image(file.file), k)


@app.get("/search/text")  # MiniLM text -> site descriptions (separate space)
def search_text(q: str, k: int = 10):
    emb = ml.embed_text(q)
    with connect() as conn:
        return conn.execute(
            """SELECT id, name, region, description,
                               1 - (description_embedding <=> %s) AS score FROM sites
                               WHERE description_embedding IS NOT NULL
                               ORDER BY description_embedding <=> %s LIMIT %s""",
            (emb, emb, k),
        ).fetchall()


@app.get("/review/queue")
def review_queue(limit: int = 50):
    with connect() as conn:
        return conn.execute(
            """SELECT it.id, it.image_id, t.label, t.tag_type, it.score
                               FROM image_tags it JOIN tags t ON t.id=it.tag_id
                               WHERE it.status='auto' ORDER BY it.score ASC LIMIT %s""",
            (limit,),
        ).fetchall()


class Review(BaseModel):
    action: str  # confirm | reject
    reviewer: str = "reviewer"


@app.post("/review/tags/{image_tag_id}")
def review_tag(image_tag_id: int, body: Review):
    status = {"confirm": "verified", "reject": "rejected"}.get(body.action)
    if not status:
        raise HTTPException(400, "action must be confirm or reject")
    with connect() as conn:
        conn.execute("UPDATE image_tags SET status=%s WHERE id=%s", (status, image_tag_id))
        conn.execute(
            "INSERT INTO tag_reviews(image_tag_id, reviewer, action) VALUES (%s,%s,%s)",
            (image_tag_id, body.reviewer, body.action),
        )
    return {"id": image_tag_id, "status": status}


class AddTag(BaseModel):
    image_id: int
    label: str
    reviewer: str = "reviewer"


@app.post("/review/tags/add")
def add_human_tag(body: AddTag):
    with connect() as conn:
        tag = conn.execute("SELECT id FROM tags WHERE label=%s", (body.label,)).fetchone()
        if not tag:
            raise HTTPException(404, "label not in controlled vocabulary")
        row = conn.execute(
            """INSERT INTO image_tags(image_id, tag_id, status) VALUES (%s,%s,'added_by_human')
                              ON CONFLICT (image_id, tag_id) DO UPDATE SET status='added_by_human'
                              RETURNING id""",
            (body.image_id, tag["id"]),
        ).fetchone()
        conn.execute(
            "INSERT INTO tag_reviews(image_tag_id, reviewer, action) VALUES (%s,%s,'add')",
            (row["id"], body.reviewer),
        )
    return {"id": row["id"], "status": "added_by_human"}
