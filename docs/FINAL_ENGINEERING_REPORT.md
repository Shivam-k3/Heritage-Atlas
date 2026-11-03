# Final engineering report (historical snapshot)

> **Superseded.** This file records the 31 October 2026 build. Its test counts (48 passed) and its
> image-to-image self-match claim are no longer current. The current verified/unverified status is in
> `docs/SUBMISSION_READINESS.md`; the current phase report is
> `docs/PHASE_1_ENGINEERING_REPORT.md`.

Date: 31 October 2026. Scope: backend, dataset pipeline, ML, database, tests and technical docs.
The frontend lane was not modified.

## 1. Summary

The backend is a working FastAPI + PostgreSQL/pgvector service for a heritage archive: sites,
uploads, asynchronous tagging/embedding, text and image search, explainable related sites, an
append-only review workflow, and Explorer Trails with distances and generated journals. It is
seeded from a real 30-site, 150-image Wikimedia Commons dataset and was exercised end to end with
the real CLIP and MiniLM models.

Verification at the end of the build:

| Check | Result |
|---|---|
| `pytest backend/tests -q` | **48 passed** |
| `ruff check backend scripts` | clean |
| `ruff format --check backend scripts` | clean |
| Dataset validation | 30 sites, 150 unique images, 0 errors, 0 warnings |
| Seeded database | 30 sites, 151 images processed (150 dataset + 1 checkpoint upload), 30 description embeddings, 734 image tags, 151/151 jobs done |
| End-to-end checkpoint | upload, worker, text search, text-to-image, image-to-image, related sites, review queue, trails summary and journal all returned 2xx |

No model-accuracy number is claimed. Hand labels and relevance judgements were not collected, so
the evaluation scripts deliberately report "not measured" instead of a fabricated score.

## 2. What was built

### Backend
- `app/routers/{sites,images,jobs,search,review,trails,users}.py`: thin handlers, request validation
  through Pydantic v2 schemas.
- `app/repositories/*`: all SQL, always parameterised. This preserves the repository's existing
  `psycopg` + `db/schema.sql` approach.
- `app/services/{geo,journal,ranking,images,licences}.py`: pure logic (haversine, journal text,
  score fusion, upload validation, licence handling) with unit tests.
- `app/ml.py`: lazy CLIP (`clip-ViT-B-32`, 512-d) and MiniLM (`all-MiniLM-L6-v2`, 384-d) loading,
  image/text embeddings, heritage tag prompts, model metadata.
- `worker.py`: `FOR UPDATE SKIP LOCKED` job claiming, retries, idempotent auto-tag replacement,
  `--once` drain mode, reconnect loop.
- `db/schema.sql` plus `db/migrations/001_backend_expansion.sql`; `init_db.py` applies schema,
  migrations and RLS setup idempotently.
- Upload deduplication by SHA-256; EXIF GPS fallback; 15 MB limit; MIME/size validation; per-image
  author, licence, licence URL and source URL.

### Search and recommendations
- Text search uses MiniLM over site descriptions.
- Text-to-image and image-to-image use CLIP only. The two spaces are never compared.
- Related sites fuse CLIP image similarity with tag Jaccard (`alpha * CLIP + (1-alpha) * Jaccard`,
  default alpha 0.6) and return the evidence pair, shared tags and both component scores.

### Verification and trails
- Review queue ordered by lowest raw score, confirm/reject actions, human-added tags, and an
  append-only `tag_reviews` history.
- AI output never overwrites the original note. Re-running a job replaces only `auto` tags.
- Trails: ordered stops, reorder, haversine legs, total km, photo counts, verified-feature summary
  and a generated journal that keeps `original_note` and `generated_summary` separate.

## 3. Dataset

Source: Wikimedia Commons, downloaded through the API with a proper User-Agent. Raw images are
gitignored; manifests and reports are committed.

| Item | Value |
|---|---|
| Sites | 30 (15 Gujarat, 15 Rajasthan) |
| Categories | 8 forts, 7 palaces, 6 temples, 4 stepwells, 3 mosques, 2 havelis |
| Images | 150 (5 per site), 150 unique |
| Size | 114.3 MB |
| Validation | 0 errors, 0 warnings |
| Licences | CC BY 2.0/3.0, CC BY-SA 2.0/2.5/3.0/4.0, CC0, No restrictions, Public domain |
| Metadata | Author, licence, licence URL, source URL, original dimensions, local path per image |

Four sites had no usable Wikipedia extract and were enriched from Wikidata descriptions; this is
recorded in the manifest. Full facts: `data/dataset/REPORT.md`, `manifest.json`, `images.json`,
`validation.json`.

Pipeline scripts in `scripts/dataset/`:
`download_wikimedia.py`, `generate_metadata.py`, `validate_images.py`, `generate_report.py`,
`commons_client.py`, and the optional `download_roboflow.py`.

## 4. Architecture decisions and deviations

1. **Kept `psycopg` + `db/schema.sql` instead of rewriting to SQLAlchemy 2/Alembic.** The existing
   repository already worked this way and `db/schema.sql` is the declared source of truth. A rewrite
   would have added risk without changing behaviour. Upgrades are idempotent SQL in
   `db/migrations/`; `init_db.py` applies both. This is the one deliberate deviation from the task
   prompt's suggested stack and is documented here and in `docs/ARCHITECTURE.md`.
2. **Preserved the frontend contract.** `GET /sites` remains a bare array with `region`/`category`
   names, and `GET /sites/{id}` keeps its shape. New filters and pagination are additive.
3. **Dependency split.** `requirements.txt` is core, `requirements-ml.txt` adds
   `sentence-transformers`, `requirements-dev.txt` adds test/lint tools, and
   `requirements-optional.txt` holds Roboflow. CI installs only the dev set, so tests stay fast.
4. **Heavy ML stays in the worker.** Only one query embedding runs inside a search request, which is
   the allowed exception.

## 5. End-to-end checkpoint (real models)

`backend/scripts/checkpoint.py`, warm models, against the seeded database:

| Step | Result |
|---|---|
| Upload a cropped Rani ki Vav photo | 202, image 151, duplicate detection on rerun |
| Worker | processed the image, CLIP embedding written, tags replaced idempotently |
| Text search: "stepwell with carved pillars and sculptures" | 101 ms; top 3 Rani ki Vav (0.534), Adalaj Stepwell (0.413), Chand Baori (0.384) |
| Text-to-image: "ancient stepwell with geometric stone steps" | 103 ms; top hits Rani ki Vav and Panna Meena ka Kund |
| Image-to-image (same crop) | 264 ms; exact self-match 1.0, then same-site photos 0.974/0.890 |
| Related sites for Rani ki Vav | Adalaj 0.804, Chittorgarh 0.800, Panna Meena 0.785, Bhadra 0.767, Hutheesing 0.726 |
| Trail summary | 2 sites, 11 photos, 91.14 km leg |
| Trail journal | generated summaries, original notes untouched, no verified tags yet |

Raw output: `data/dataset/checkpoint.json`, `checkpoint.log`. Timings are single warm queries, not a
benchmark.

Observed tag distribution over the 151 processed images: `jali work` 143, `staircases` 90, `domes`
66, `decorative facade` 57, `sculptural carvings` 51, `water tank` 50. This is output, not accuracy;
it shows CLIP over-tags generic architectural features, which is why tag overlap is only 40% of the
related-site score.

## 6. Bugs found and fixed during verification

- pgvector `Vector` cannot be passed directly to `numpy.asarray`; related sites now calls
  `.to_numpy()`.
- PIL `Image.verify()` invalidated the image before reopening; validation order corrected.
- Windows temp-file handle leak in `save_image`; the temporary file is now closed before rename.
- Worker used the `connect()` context manager as if it were a connection; switched to
  `open_connection()` for the long-lived worker connection.
- Checkpoint crashed when printing a thin-space character on a cp1252 console; stdout is now UTF-8.
- Checkpoint assumed every upload creates a job; duplicate uploads now report a skipped job.
- Removed unused imports and formatting issues found by ruff.

## 7. Tests and code quality

48 tests: pure units for haversine, ranking, journal text and licence handling; API tests for sites,
upload, search, review, trails and users; worker tests for retries/idempotency. Database tests run
against a real pgvector database and refuse to run unless the database name ends in `_test`.

`ruff` selects `E, F, I, B, UP, S` and passes on `backend/` and `scripts/`. SQL is parameterised;
route handlers are thin; model loading is lazy so CI does not download models.

## 8. Integration readiness

- Frontend needs only `GET /sites` and `GET /sites/{id}` today; both are implemented and tested.
- Additional endpoints for upload, search, review and trails are documented in `docs/API.md`,
  `docs/api-contracts.md` and the generated `docs/openapi.json`.
- CORS defaults to `http://localhost:3000`; uploaded files are served at `/files/...`.
- Search hit field names match the frontend types (`name`, `image_id`, `url`, `score`).
- `score` must be shown as a raw similarity, and tag provenance must stay visible.

## 9. Known limitations and critical issues

1. **No hand labels or relevance judgements**, so tagging F1 and search precision@5 are not
   measured. Scripts and formats are ready; this is a data-collection task, not a code gap.
2. **No authentication or authorisation.** Reviewer identity is a plain string and `/users` is open.
   Acceptable for a hackathon demo, not for production.
3. **Docker Compose was not executed** in this environment (Docker unavailable). The service file
   uses the official `pgvector/pgvector:pg16` image and was reviewed, but not runtime-tested here.
4. **CLIP over-tags generic features** (`jali work` on 143/151 images). Threshold tuning needs hand
   labels; until then, related sites intentionally weight CLIP higher.
5. **No hosted deployment or load test.** Latencies above are single queries on a local database.
6. **Four descriptions are Wikidata-only**, shorter than the Wikipedia extracts.
7. **Image-to-image includes the query image itself** when that exact image is already indexed
   (checkpoint scored 1.0). A production search should exclude the query image id.
8. **`init_db.py` uses idempotent SQL, not a migration framework.** Fine at this size; revisit if
   schema history or rollbacks become necessary.

## 10. Next actions

1. Hand-label 30-50 images (`eval_tagging.py --template`) and tune `FEATURE_THRESHOLD` and prompts.
2. Judge top-5 results for 10-15 queries, then run `eval_search.py`.
3. Add authentication and reviewer roles before exposing review actions publicly.
4. Exclude the query image from image-to-image results.
5. Run `docker compose up -d db` and the full README flow on a clean machine.
6. Wire the frontend pages to upload/search/review/trails endpoints (frontend lane).

## 11. Reproduction commands

    docker compose up -d db
    cp .env.example .env
    cd backend && python -m venv .venv && .venv\Scripts\activate
    pip install -r requirements-ml.txt
    python scripts/init_db.py
    python scripts/load_dataset.py
    python worker.py --once
    python scripts/embed_descriptions.py
    python scripts/checkpoint.py
    pytest tests -q

Dataset rebuild: `python -m scripts.dataset.download_wikimedia`, then `generate_metadata`,
`validate_images`, `generate_report`.
