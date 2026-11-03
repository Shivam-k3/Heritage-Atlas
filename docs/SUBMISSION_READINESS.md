# Submission readiness — Heritage Atlas backend

Date: 3 November 2026. Scope: FastAPI backend, Python services, database schema, ML code, ingestion,
worker, backend tests and backend documentation. No frontend source file was edited. Nothing was
pushed, merged or rewritten.

This report separates **executed** results from **written but skipped** tests and from **blocked**
work. A skipped database test is not a passing test.

## 1. Implemented features

| Area | Status |
|---|---|
| Sites | Create, list, get, update; filters by region/category/tag/verified; draft confirm/reject/merge |
| Uploads | Single and batch upload; SHA-256 dedupe; size and format validation; per-image author/licence/source |
| Jobs | Database-backed queue, worker leases, stale recovery, retry limit, exponential backoff, terminal failure |
| AI tagging | `heritage-v2`: 7 features, 4 prompts each, aggregated CLIP embeddings, per-label thresholds, optional negative prompts, no forced predictions, model/prompt provenance |
| Search | Text-to-site (MiniLM), text-to-image (CLIP), image-to-image (CLIP); self and cross-site exclusion; optional per-site cap; pagination |
| Related sites | CLIP image similarity plus feature-tag overlap, explainable evidence |
| Review | Queue with public URL and provenance; confirm/reject/add; append-only `tag_reviews`; human decisions survive reprocessing |
| Folder ingestion | Recursive scan, EXIF orientation/GPS/time, SHA-256 dedupe, 300 m Haversine clustering, draft sites, dry run, resumable batches |
| Explorer Trails | Create/list/get/update; add/remove/reorder stops; ordered coordinates; Haversine legs; straight-line mode; missing-coordinate report; EXIF-derived trails; template journal |
| Health/files | `/health`, read-only `/files/...` static serving |

## 2. Verified on real images

The folder-ingestion scan path was exercised on the 160 real files under `data/raw` in dry-run mode.
That run found:

- 2 files with EXIF GPS;
- 0 files with a usable capture timestamp;
- 0 duplicate files and 0 corrupt files.

This verifies recursive scanning, extension filtering, hashing, EXIF reading and clustering logic.
It does **not** verify database writes, model inference, search or trail generation from those files.
EXIF coverage is low, so an EXIF-derived trail over this dataset would contain very few or no stops.

The earlier dataset/checkpoint runs described in `docs/FINAL_ENGINEERING_REPORT.md` are historical.
Their counts are not repeated here as current results.

## 3. Database-dependent features still unverified

No PostgreSQL or Supabase connection was available. `TEST_DATABASE_URL` is unset, so all 45
database tests were skipped. A skipped test is not a passing test. The following are implemented but
unproven against a real database:

- **Schema and migrations:** `db/schema.sql`, `db/migrations/001_backend_expansion.sql`,
  `db/migrations/002_phase1.sql`, the pgvector extension, and the RLS statements in
  `backend/scripts/init_db.py` have not been applied to Supabase.
- **Sites:** list/filter, create, detail, update, related sites, drafts, confirm, reject and merge.
- **Uploads and images:** single and batch upload, SHA-256 dedupe, metadata/tags/reprocess, stored
  `/files/...` URLs, and job creation.
- **Jobs and worker:** claim/lease, stale recovery, retry/backoff, terminal failure, idempotent
  reprocessing, and embedding/tag writes.
- **Search:** MiniLM text search, CLIP text-to-image, CLIP image-to-image, filters, pagination,
  query-image exclusion and cross-site exclusion.
- **Review:** queue, reviewer list, confirm/reject, human-added tags, append-only history, and
  preservation of human decisions during reprocessing.
- **Folder ingestion:** scanning into PostgreSQL, ingest batches, draft clustering and resumability.
- **Trails:** create/list/get/update, add/remove/reorder stops, summary legs/total/missing
  coordinates, EXIF-derived trails and journal generation.
- **Users:** create/list/get.
- **Health:** the database branch of `GET /health`.
- **Scripts:** `load_dataset.py`, `embed_descriptions.py`, `checkpoint.py` and `smoke_test.py` need a
  live API, worker and database; none were executed here.
- **Frontend real API flows:** explore/site detail, search, upload, review, trails and related sites
  are implemented in the local frontend working tree, but that work is not part of this backend
  commit and has not been exercised against a live database.

No database was reset, truncated or modified in this sprint.

## 4. API endpoints ready for the frontend

The generated contract is `docs/openapi.json` (34 paths). The full behaviour is in `docs/API.md`;
the quick map is `docs/api-contracts.md`.

Frontend-critical endpoints:

| Method | Path | Notes |
|---|---|---|
| GET | `/sites` | Bare array; existing shape preserved |
| GET | `/sites/{id}` | Detail plus images and tags |
| GET | `/sites/{id}/related` | `k`, `alpha`; raw scores |
| GET | `/sites/drafts` | Unverified EXIF clusters |
| POST | `/sites/{id}/confirm` | Promote a draft |
| POST | `/sites/{id}/reject` | Keep photos, mark rejected |
| POST | `/sites/{id}/merge` | Move photos to a canonical site |
| POST | `/images/upload` | 202; multipart |
| POST | `/images/upload-batch` | Partial success with per-file errors |
| GET | `/images/{id}` | Metadata plus tags |
| GET | `/images/{id}/tags` | Tag array |
| POST | `/images/{id}/reprocess` | 202 |
| GET | `/jobs/{id}` | Job status and retry count |
| GET | `/search/text` | MiniLM site search |
| GET | `/search/images` | CLIP text-to-image |
| POST | `/search/by-image` | CLIP image-to-image; `cross_site`, `exclude_image_id`, `max_per_site` |
| GET | `/review/queue` | Public `url`, raw score, provenance |
| GET | `/review/reviewers` | Fixed demo identifiers |
| POST | `/review/tags/{image_tag_id}` | confirm/reject |
| POST | `/review/tags/add` | Human-added tag |
| GET | `/review/history/{image_tag_id}` | Append-only audit |
| POST | `/trails` | Create |
| GET | `/trails` | List |
| GET | `/trails/{id}` | Stops include `lat`/`lon` |
| PATCH | `/trails/{id}` | Title, description, visibility |
| POST | `/trails/{id}/stops` | Append stop |
| DELETE | `/trails/{id}/stops/{stop_id}` | Remove and renumber |
| PATCH | `/trails/{id}/stops/reorder` | Permutation of stop ids |
| POST | `/trails/from-images` | EXIF-derived trail; reports used/skipped |
| GET | `/trails/{id}/summary` | Legs, total, `distance_mode`, `missing_coordinates` |
| GET | `/trails/{id}/journal` | Original note and generated summary kept separate |
| GET | `/health` | Database and model state |

Integration rules for the frontend:

- Show tag `status` (`auto`, `verified`, `rejected`, `added_by_human`) and model provenance.
- Never render a raw cosine score as a percentage or confidence.
- Never label a trail distance as driving/road distance. It is straight-line Haversine.
- Rejected tags must not appear as active tags.
- Use `/files/...` URLs as returned; never build filesystem paths.

## 5. Trail API test results

Pure tests that ran and passed:

- Haversine distance and range validation.
- Ordered legs and rounding.
- Missing-coordinate reporting is unique and in stop order.
- EXIF visit grouping: one stop per site, earliest capture first.
- Unusable rows are skipped.

Database tests that were written but **skipped** here:

- Create/list/get/update trail.
- Add multiple stops, reorder, remove and renumber.
- Empty trail summary.
- Missing-coordinate summary.
- EXIF-derived trail with used/skipped counts.
- Journal response and original-note preservation.
- Error cases (404/400/422).

Run them after configuring a `_test` database:

    $env:TEST_DATABASE_URL = "postgresql://.../atlas_test?sslmode=require"
    backend\.venv\Scripts\python.exe -m pytest backend/tests/test_trails_api.py -q

## 6. ML evaluation status

Blocked. `data/dataset/tag_annotations.csv` does not exist, so there are no human labels for tuning or
evaluation. All seven thresholds in `backend/app/feature_prompts.json` remain `null`.

Consequences:

- The worker does not emit automatic feature tags. An empty tag list is the intended safe outcome.
- Macro-F1, per-feature precision/recall, baseline-vs-revised-vs-negative comparison and the
  logistic-regression probe cannot be reported.
- No metric in this repository was invented or reused from the historical report.

To unblock: create the annotation sheet, label tuning sites, run
`python backend/scripts/tune_tagging.py --write` and then `python backend/scripts/eval_tagging.py`
against held-out sites. Keep thresholds `null` until that evaluation exists.

## 7. Security findings

| Finding | State |
|---|---|
| CORS | Restricted to `CORS_ORIGINS` (default `http://localhost:3000`) |
| Write endpoints | **No authentication or API key.** Anyone who can reach the API can write |
| Reviewer identity | Fixed demo list (`asha,ravi,guest`), not authentication; impersonation is possible |
| Upload size | `MAX_UPLOAD_MB` (default 15), enforced while streaming |
| File type | Pillow verification; only JPEG, PNG and WebP accepted |
| SQL injection | All values parameterised; dynamic identifiers come from whitelists |
| Secrets | `.env` is gitignored; `.env.example` has placeholders; no credential committed |
| Error responses | Generic 503/409/500 messages; internal details are logged, not returned |
| Public images | Uploaded originals are served read-only at `/files/...`; intended for the demo |
| Image search upload | Read is bounded to `max_bytes + 1` before rejection |

Recommendation: do not expose the write endpoints on the public internet for the demo. If that is
unavoidable, put the API behind a reverse proxy with an API key or real authentication. An API key
was not added because the frontend contract and deployment target are not settled; adding one now
would require coordinated frontend changes.

## 8. Test results

Commands were run from the repository root with `backend/.venv`:

| Command | Result |
|---|---|
| `pytest backend/tests -q` | **43 passed, 45 skipped, 0 failed** (1.27s) |
| `ruff check backend scripts` | **All checks passed** |
| `ruff format --check backend scripts` | **71 files already formatted** |
| `mypy` | **Success: no issues found in 45 source files** |
| `app.openapi()` | **34 paths** written to `docs/openapi.json` |

The 45 skips are database tests. They require `TEST_DATABASE_URL` pointing at a database whose name
ends in `_test`. The guard in `backend/tests/conftest.py` was not weakened.

Not executed: database tests, full ingestion to PostgreSQL, real search/review/worker runs, Supabase
connectivity, ML evaluation. `backend/scripts/smoke_test.py` was updated to match current semantics
(zero auto tags is valid while thresholds are `null`; the query image is excluded from
image-to-image; review uses a configured reviewer) but needs a running API, worker, database and
three real photos, so it was not executed here.

## 9. Deployment requirements

1. Python 3.11+.
2. PostgreSQL 15+ with the `vector` extension (local Docker, CI image or Supabase).
3. Install `backend/requirements.txt` for the API; `backend/requirements-ml.txt` for the worker and
   query-time embeddings. CPU-only PyTorch is supported.
4. Prefetch `clip-ViT-B-32` and `all-MiniLM-L6-v2`, or mount a populated `HF_HOME`.
5. Set `DATABASE_URL`, `UPLOAD_DIR`, `CORS_ORIGINS`, `MAX_UPLOAD_MB`, `REVIEWERS`, `JOB_*`.
6. For Supabase, use the session pooler on port 5432 with `sslmode=require`; run
   `backend/scripts/init_db.py` once; create an empty `atlas_test` database for tests.
7. Start the API (`uvicorn app.main:app`) and the worker (`python backend/worker.py`) as separate
   processes.
8. Serve `/files/...` from the same host or configure the frontend base URL accordingly.

See `README.md` for the full command sequence and the Supabase checklist.

## 10. Critical remaining blockers

1. **Database integration is unverified.** No Supabase or local PostgreSQL connection exists, so the
   45 database tests and all DB-backed flows are unproven.
2. **No human labels, so no automatic tags.** All thresholds are `null`; the review queue will be
   empty until tags exist. Do not claim AI accuracy.
3. **Low EXIF coverage.** Only 2 of 160 local files have GPS and none have a capture timestamp, so
   EXIF-derived trails are not demonstrable on that folder.
4. **No write authentication.** Do not expose the API publicly without a proxy or auth.
5. **Frontend integration is uncommitted and live-unverified.** The Trails, related-sites, review and
   history UI exists in the local frontend working tree and calls the real API, but it is not part of
   this backend commit and has not been exercised against a live database. See
   `docs/FRONTEND_HANDOFF.md`.

## 11. Recommended final demonstration sequence

1. `GET /health` — show database and model state.
2. `GET /sites` — show the map/list data and provenance fields.
3. `GET /sites/{id}` — show images, author, licence and source URL.
4. `POST /images/upload` with a real photo — show 202, then `GET /jobs/{id}` and the processed image.
   If thresholds are still `null`, state clearly that the model intentionally emits no automatic tag.
5. `POST /review/tags/add` with a human label — show the `added_by_human` provenance, then
   `GET /review/history/{image_tag_id}` to show the append-only record.
6. `GET /search/text?q=stepwell` and `GET /search/images?q=carved stone` — show raw scores and tags.
7. `POST /search/by-image` with `cross_site=true` — show the query image and its site are absent.
8. `POST /trails` -> add two or three stops -> `PATCH .../reorder` -> `GET .../summary` — show
   ordered coordinates, Haversine legs, `distance_mode: "straight_line"` and `missing_coordinates`.
9. `GET /trails/{id}/journal` — show `original_note` beside `generated_summary`.
10. `POST /trails/from-images` with an image set that has timestamps and coordinates, if available.
    Otherwise explain that the local folder lacks the required EXIF and do not fake it.

Do not demo a trail distance as a road distance, and do not show a raw cosine score as a confidence
percentage.

## 12. Supabase smoke-test sequence for 4 November

Run from the repository root in PowerShell. Use the **session pooler** (IPv4, port 5432). Do not use
the transaction pooler and never run `init_db.py --reset` against Supabase.

### 12.1 Set environment variables for this shell only

```powershell
$env:DATABASE_URL = "postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/postgres?sslmode=require"
$env:TEST_DATABASE_URL = "postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/atlas_test?sslmode=require"
$env:CORS_ORIGINS = "http://localhost:3000"
$env:UPLOAD_DIR = "$PWD\uploads"
```

Do not write these values to a tracked file. `.env` is gitignored.

### 12.2 Create the test database and enable pgvector

In the Supabase SQL editor (or with `psql "$env:DATABASE_URL"`):

```sql
create database atlas_test;
```

Then, in the **app** database:

```sql
create extension if not exists vector;
```

The test guard only accepts a database name ending in `_test`. The pytest fixtures create and
truncate tables in `atlas_test`; never point `TEST_DATABASE_URL` at `postgres`.

### 12.3 Apply the schema and migrations (idempotent, no reset)

```powershell
backend\.venv\Scripts\python.exe backend\scripts\init_db.py
```

Expected output: `Schema applied.`, two migration lines, then
`Row level security enabled on every table.`

### 12.4 Run the full backend suite against Supabase

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests -q -rs
```

Expected: **88 passed, 0 failed, 0 skipped**. Any skip means `TEST_DATABASE_URL` is not visible to
the process. This is the step that converts the 45 previously skipped database tests into real
results.

### 12.5 Start the API and worker

Terminal 1:

```powershell
$env:PYTHONPATH = "backend"
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 (uses the same `DATABASE_URL`; the first run downloads CLIP and MiniLM):

```powershell
backend\.venv\Scripts\python.exe backend\worker.py
```

### 12.6 Health check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 5
```

Expect database `ok`. If the database is unreachable the endpoint returns 503 rather than a fake
success.

### 12.7 End-to-end upload, worker, search and review

Use three real photos that are not already in the database:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\smoke_test.py `
  --stepwell "C:\path\to\stepwell.jpg" `
  --fort "C:\path\to\fort.jpg" `
  --temple "C:\path\to\temple.jpg" `
  --timeout 900
```

Expected last line: `SMOKE TEST PASSED`. A zero auto-tag result is valid while every threshold in
`backend/app/feature_prompts.json` is `null`.

### 12.8 Live Trails check

```powershell
$base = "http://127.0.0.1:8000"
$sites = Invoke-RestMethod "$base/sites?limit=2"

$trail = Invoke-RestMethod -Method Post -Uri "$base/trails" -ContentType "application/json" -Body (
  @{ title = "Smoke trail"; description = "4 Nov check"; created_by = "smoke"; is_public = $false } |
  ConvertTo-Json
)

foreach ($site in $sites) {
  Invoke-RestMethod -Method Post -Uri "$base/trails/$($trail.id)/stops" -ContentType "application/json" -Body (
    @{ site_id = $site.id } | ConvertTo-Json
  ) | Out-Null
}

$full = Invoke-RestMethod "$base/trails/$($trail.id)"
$ids = @($full.stops | Sort-Object stop_order -Descending | ForEach-Object { $_.id })
Invoke-RestMethod -Method Patch -Uri "$base/trails/$($trail.id)/stops/reorder" `
  -ContentType "application/json" -Body (@{ stop_ids = $ids } | ConvertTo-Json) | Out-Null

Invoke-RestMethod "$base/trails/$($trail.id)/summary" | ConvertTo-Json -Depth 5
Invoke-RestMethod "$base/trails/$($trail.id)/journal" | ConvertTo-Json -Depth 5
```

Check:

- `summary.distance_mode` is `"straight_line"` and `legs` follow the reordered stops.
- `missing_coordinates` lists site ids whose `lat`/`lon` are null; it is not an error.
- `journal.entries[].original_note` is separate from `generated_summary`.
- `POST /trails/from-images` returns 400 when no image has both a capture time and site coordinates.
  Do not fake EXIF data to make it pass.

### 12.9 Record the results

Update this file with the actual date, command output and any failure. Do not mark a check as passed
unless it ran against the live database. If Supabase is still unavailable on 4 November, keep the
blocked status and use the local demonstration sequence in section 11.
