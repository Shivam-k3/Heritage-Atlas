# Architecture

## Components
```
Next.js + Leaflet  --REST/JSON-->  FastAPI  --SQL-->  PostgreSQL + pgvector
                                      |                      ^
                                      |  jobs table          |
                                      v                      |
                                   Worker (Python) ----------+
                                   CLIP + MiniLM
Image files: local ./uploads (dev) -> S3-compatible storage (production)
```
| Component | Responsibility |
|---|---|
| Frontend | Map, search, upload, site pages, trails, review queue |
| API (FastAPI) | Validation, HTTP, queries, query-time embedding of one search string or photo |
| Worker | Image embedding, zero-shot tagging, description embedding, retries |
| Database | Sites, images, tags, reviews, trails, jobs, vectors |

## Embedding spaces (critical)
| Space | Model | Dim | Stored in | Used for |
|---|---|---|---|---|
| CLIP | clip-ViT-B-32 | 512 | images.clip_embedding | Text-to-image, image-to-image, tagging, related sites |
| MiniLM | all-MiniLM-L6-v2 | 384 | sites.description_embedding | Text-to-text search |
CLIP and MiniLM vectors are never compared. If results from two spaces are merged, use
reciprocal rank fusion (rank-based), not raw scores. Confirm dimensions from the exact model if it changes.

## Upload flow
1. API stores the file, creates the site if needed, inserts `images` row and a `jobs` row, returns `job_id`.
2. Worker claims a job with `FOR UPDATE SKIP LOCKED`, so several workers can run safely.
3. Worker embeds the image, writes tags with status `auto` and raw cosine scores, embeds the description.
4. On error the job is marked `failed` with the traceback; the file and notes are untouched.
5. A running job older than `JOB_LEASE_SECONDS` is treated as abandoned and requeued; that counts as
   an attempt. Retries wait an exponential backoff and stop at `JOB_MAX_RETRIES`.

## Tagging
Prompts live in `app/feature_prompts.json` with a version string (`heritage-v2`). Seven stable
feature labels are encoded as 4 prompt variants each, normalised, averaged and normalised again.
Site type is never predicted: the site record owns `category`. Images are compared only against
the aggregated feature embeddings; the result is a raw cosine per label.
A feature is emitted only when its score reaches its own per-label cut-off. Missing cut-offs
(`null`) mean the feature cannot be emitted, so "no confident feature" is a valid result. Cut-offs
are tuned on human labels from tuning sites only (`scripts/tune_tagging.py`); no universal
threshold is used. `scripts/eval_tagging.py` compares the old baseline, prompt aggregation and
aggregation with negative prompts; the simpler method stays unless validation improves.

## Folder ingestion
`scripts/ingest_folder.py` scans a local folder recursively, validates and hashes files, extracts
EXIF GPS/time, clusters GPS points within a configurable radius (default 300 m, Haversine) and
creates draft sites plus processing jobs. Missing GPS files go to a separate draft bucket. Draft
clusters are never canonical: reviewers confirm, rename, merge or reject them through the API.
Re-running the folder is safe because content is deduplicated by SHA-256.

## Verification and provenance
Tag status: `auto` -> `verified` | `rejected`; humans can add `added_by_human`.
Every decision appends a row to `tag_reviews` (reviewer, action, time). Status changes never delete history.

## Related sites
`S = alpha * cosine(mean CLIP image embedding of A, of B) + (1 - alpha) * Jaccard(tags A, tags B)`
Tags used: verified and human-added if present, otherwise auto. alpha is chosen experimentally (start 0.6).
The response includes shared tags and the nearest photo pair so the reason can be shown.

## Trails
A trail is an ordered list of stops. Distance uses the haversine formula (straight line), reported as
`distance_mode: "straight_line"` and never as road distance. Stops without coordinates are listed in
`missing_coordinates` and excluded from leg and total calculations.
`POST /trails/from-images` groups stored photographs into one stop per site, ordered by the earliest
EXIF `captured_at`; images without a timestamp or site coordinates are counted and skipped.
The journal is generated from templates (not an LLM): site, category, verified features, photo count, and
the original field note shown verbatim and separately from generated text, which is labelled "generated".

## Scalability story
- Async workers scale horizontally; the queue is the database today, replaceable by Redis/Celery.
- HNSW indexes give approximate nearest-neighbour search; a dedicated vector store is a later swap.
- Embeddings are computed once. The API is stateless. Images move to object storage behind a CDN.
- Every model run should be reproducible: store model name and prompt version (roadmap: `model_runs`).

## Limitations (state them in the deck)
Zero-shot tags can be wrong on unusual photos; the dataset is small; descriptions are mostly English;
trail distances are straight lines; geocoded locations may need correction; no authentication in the demo.

## Repo layout
```
db/schema.sql          schema (source of truth); db/migrations for idempotent upgrades
backend/app            main.py, routers/, repositories/, services/, ml.py, db.py
backend/worker.py      job processor
backend/scripts        init_db, dataset loader, embeddings, checkpoint, eval scripts
backend/tests          pytest
frontend/              Next.js app
docs/                  PRD, API, ARCHITECTURE, DATASET, EVALUATION, TASKS, WORKFLOW
DESIGN.md              UI design system
AGENTS.md              rules for AI coding agents
```

## Persistence choice
The project keeps the existing raw `psycopg` repositories and `db/schema.sql` rather than SQLAlchemy
2/Alembic. Schema changes are idempotent SQL in `db/migrations/`; `init_db.py` applies the schema,
then every migration, then RLS. This was chosen to avoid rewriting a working data layer; revisit if
schema history or rollbacks become necessary.
