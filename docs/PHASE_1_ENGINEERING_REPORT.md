# Phase 1 engineering report — AI tagging, retrieval, ingestion and reliability

Date: 2 Nov 2026. Scope: backend, Python ML, database, migrations, backend scripts and tests.
No frontend source was edited in this phase. No push or merge was performed.

Scores in this report are raw CLIP or MiniLM cosine similarities in `[-1, 1]`. They are never
probabilities or confidence percentages. No accuracy, scalability or deployment number is claimed
unless a script produced it.

> Final sprint update (3 Nov 2026): the current non-database results are **43 passed, 45 skipped**;
> `ruff check` clean; `ruff format --check` clean over 71 files; `mypy` clean over 45 source files;
> `docs/openapi.json` has 34 paths. The 45 skips are database tests because `TEST_DATABASE_URL` is
> unset. They are **not** reported as passed. See `docs/SUBMISSION_READINESS.md` for the full
> verified/unverified status.

## 1. What this phase changed

| Area | Before | After |
|---|---|---|
| Site type | CLIP argmax over `SITE_TYPES` written as a tag | Never predicted; the site record owns `category` |
| Feature vocabulary | 9 labels, one prompt each | 7 stable labels, 4 prompt variants each, versioned config |
| Acceptance | Universal `0.22` cut-off, always emitted up to 4 tags | Per-label cut-off; `null` means never emitted; empty result allowed |
| Prompt config | Hardcoded in `app/ml.py` | `backend/app/feature_prompts.json` version `heritage-v2` |
| Negative prompts | None | 2 per feature, scored and compared, not assumed to help |
| Evaluation | No hand-label sheet, no site-wise split | Annotation template, 60/20/20 site split, baseline/revised/negative comparison, few-shot probe |
| Image-to-image | Query image and same-site images could appear | Query image always excluded; `cross_site=true` excludes the whole site |
| Search payload | No tags or attribution | Tags with status/provenance, author, licence, URLs |
| Folder ingestion | None | Recursive scan, EXIF GPS/time, SHA-256 dedupe, draft clusters, dry-run |
| Review queue | No image URL, free-text reviewer | Public `/files/...` URL, fixed reviewer list, append-only history |
| Jobs | A killed worker left `running` forever | Lease expiry, retry count, backoff, terminal failure |
| Types/CI | mypy had 3+ errors and was not in CI | mypy clean over 44 files and enforced in CI |

## 2. Files changed

Backend app:
- `backend/app/ml.py`: prompt aggregation, negative scoring, no site-type output, model metadata.
- `backend/app/vocabulary.py`, `backend/app/feature_prompts.json`: versioned prompt config.
- `backend/app/services/evaluation.py`: pure site split, threshold tuning, prediction, metrics.
- `backend/app/services/ingestion.py`: folder scan, Haversine clustering, cluster names.
- `backend/app/services/images.py`: EXIF GPS/time extraction and orientation handling.
- `backend/app/routers/search.py`: self/same-site exclusion, diversity cap, metadata enrichment.
- `backend/app/repositories/search.py`: `exclude_image_id` / `exclude_site_id` filters.
- `backend/app/routers/review.py`, `backend/app/repositories/review.py`: reviewer list, URL, provenance.
- `backend/app/routers/images.py`, `backend/app/routers/ingestion.py`, `backend/app/routers/sites.py`:
  batch upload, batch progress, draft-site confirm/reject/merge.
- `backend/app/schemas.py`: `SearchImageOut` metadata, draft and ingest schemas.
- `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`: env config, connection, routers.
- `backend/worker.py`: claim identity, lease recovery, retry backoff, terminal failure.

Scripts and tests:
- `backend/scripts/eval_tagging.py`, `tune_tagging.py`, `eval_fewshot.py`.
- `backend/scripts/ingest_folder.py` (`--dry-run`).
- `backend/scripts/eval_search.py`, `eval_review_stats.py`, `checkpoint.py`, `smoke_test.py` (mypy fixes).
- `backend/tests/test_tagging.py`, `test_eval_metrics.py`, `test_search_api.py`, `test_worker.py`,
  `test_ingestion.py`, `test_review_api.py`.

Database, tooling and docs:
- `db/schema.sql`, `db/migrations/002_phase1.sql`.
- `pyproject.toml` (mypy), `.github/workflows/ci.yml`, `Makefile`, `backend/requirements-dev.txt`.
- `docs/API.md`, `docs/api-contracts.md`, `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`,
  `docs/DATASET.md`, `docs/openapi.json`, `README.md`.

Uncommitted frontend changes were already present in the working tree and were left untouched.

## 3. Database migration

`db/migrations/002_phase1.sql` is idempotent and safe on a database created by
`001_backend_expansion.sql`:

- `sites`: `status` (`canonical` default, `draft`, `rejected`, `merged`), `source`,
  `merged_into_site_id`.
- `images`: `captured_at`, `exif` JSONB.
- `jobs`: `claimed_at`, `worker_id`, `available_at`.
- `ingest_batches`: one row per folder run with counts, GPS count, clusters and JSON report.
- Review provenance remains append-only in `tag_reviews`; no destructive migration.

Apply with `python backend/scripts/init_db.py` (it runs `schema.sql` plus pending migrations).

## 4. API changes and examples

Existing fields are preserved. Image-to-image defaults keep the old semantics.

### Search image hit

```json
[{
  "image_id": 4,
  "site_id": 1,
  "name": "Rani ki Vav",
  "region": "Gujarat",
  "category": "stepwell",
  "url": "/files/ab/abc.jpg",
  "score": 0.83,
  "author": "A. Photographer",
  "licence": "CC BY-SA 4.0",
  "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
  "source_url": "https://commons.wikimedia.org/wiki/File:...",
  "tags": [{
    "id": 9, "label": "jali work", "tag_type": "feature", "score": 0.31,
    "status": "verified", "model_name": "clip-ViT-B-32",
    "model_version": "clip-ViT-B-32", "prompt_version": "heritage-v2"
  }]
}]
```

Rejected tags are omitted. `url` is always a browser-loadable `/files/...` path, never a storage
path. Tag status is `auto | verified | rejected | added_by_human`.

### Image-to-image

`POST /search/by-image` multipart `file`, plus `k`, `offset`, `cross_site`,
`exclude_image_id`, `max_per_site`.
- Default (`cross_site=false`): the exact stored image is excluded when the SHA-256 matches.
- `cross_site=true`: every image with the query image's `site_id` is excluded. With no known site,
  only the exact image is excluded.
- `max_per_site` is a best-effort page-level diversity cap, applied after `offset`.

### Ingestion and drafts

- `GET /ingest/batches`, `GET /ingest/batches/{id}`: batch progress and per-file report.
- `GET /sites/drafts`: draft clusters with `images` count and `image_ids`.
- `POST /sites/{id}/confirm | reject | merge` (`{"target_site_id": 12}`): only `status='draft'`.
- `POST /images/upload-batch`: multiple browser files; per-file errors do not abort the batch.

### Review

- `GET /review/queue`: adds `url`, `author`, `licence`, `licence_url`, `source_url`, model and
  prompt provenance.
- `GET /review/reviewers`: fixed demo list from `REVIEWERS` (default `asha,ravi,guest`).
- Unknown reviewer ids return 400. This is an audit label, not authentication.

## 5. Tagging behaviour before and after

Before (pre-fix code): CLIP argmax always produced a site type, nine features were scored from one
generic prompt each, and any feature above a universal `0.22` was emitted, up to four. The prior
real-image run over-tagged generic features: `jali work` on 143/151 images and `staircases` on
90/151 (source: `docs/FINAL_ENGINEERING_REPORT.md`).

After: site type is never emitted. Seven labels are scored against normalized means of four prompt
embeddings each. A feature is emitted only when its per-label cut-off is set and its raw cosine
reaches it. All cut-offs are currently `null`, so the worker intentionally emits no auto feature
tags instead of forcing predictions. This is a deliberate no-label outcome, not a model failure.

Negative prompts exist per feature but are not used by default. `eval_tagging.py` computes the
baseline, revised aggregation and aggregation-minus-negatives on the same held-out sites so the
negative method is kept only if validation improves.

## 6. Manual labels and evaluation status

Human feature labels: **not collected**. `data/dataset/tag_annotations.csv` does not exist.
No label was derived from CLIP, existing tags or review status. The sheet is created with:

```bash
python backend/scripts/eval_tagging.py --template
```

Consequently:
- Per-feature precision, recall, F1, macro-F1, micro-F1, confusion, false-positive frequency and
  no-confident-feature frequency: **not measured**.
- Threshold tuning: **not run**; all thresholds remain `null`.
- Few-shot probe: framework implemented, but there are not enough explicit verified/rejected
  decisions. It writes `insufficient_labels` and makes no quality claim.
- Search precision@5: **not measured** (no `search_judgements.json`).

The split is deterministic per `site_id` (60/20/20). With 30 sites it is about 15 train, 11 tune and
4 test sites (~20 test photos), which is exploratory and not a generalisation claim.

## 7. Retrieval before and after

Before: `/search/by-image` embedded the upload and ranked every image, so the query image could
rank first and images from its own site dominated the page.

After: the upload's SHA-256 is looked up before ranking. If it matches a stored image, that image
and its site are known. The query image is always filtered out by `i.id <> %s`; `cross_site=true`
adds `i.site_id <> %s`. A temporary upload with no match excludes only `exclude_image_id` when the
caller supplies it. `max_per_site` limits how many hits one other site may contribute.

Tests written for this (require a test database): `test_by_image_excludes_the_query_image`,
`test_by_image_cross_site_excludes_every_image_from_the_query_site`,
`test_by_image_with_unknown_site_excludes_only_the_exact_image`,
`test_by_image_can_return_an_empty_result`, `test_by_image_diversity_caps_one_site_per_page`,
`test_by_image_respects_k_and_offset`, and
`test_image_search_includes_active_tags_and_provenance`.

**Status:** implementation done; API tests **not executed here** because no PostgreSQL/pgvector
instance or Docker is available. They are not mocked.

## 8. EXIF ingestion results on real files

Command:

```bash
python backend/scripts/ingest_folder.py data/raw --dry-run
```

Real files under `data/raw` (downloaded Wikimedia dataset, not phone photos):

| Measure | Result |
|---|---|
| Files scanned | 160 |
| Accepted | 160 |
| Duplicates | 0 |
| Rejected/corrupt | 0 |
| Files with GPS | 2 |
| Location clusters at 300 m | 2 (sizes 1, 1) |
| Files with capture timestamp | 0 |

GPS files: `amber-fort/d2c60f13b6a7422d.jpg` and `jaisalmer-fort/1f3ceb6218a466e5.jpg`.
This confirms the EXIF path works on real files, but the dataset is web photography, so GPS coverage
is 2/160 (1.25%). It is **not** evidence that a phone trip folder will have the same coverage. No
corrupt or duplicate sample existed in this folder, so those branches were exercised only by the
synthetic dry-run test.

Full database ingestion (draft sites, jobs, reprocessing) was **not run** because no database is
available.

## 9. Job recovery

Implemented in `backend/worker.py`:
- Claim writes `status='running'`, `claimed_at=now()`, `worker_id`, keeps
  `FOR UPDATE SKIP LOCKED`.
- A running job older than `JOB_LEASE_SECONDS` is returned to `pending` and counts as an attempt,
  so a job that kills its worker cannot loop forever.
- At `JOB_MAX_RETRIES` the job becomes `failed` and the image is marked `failed`.
- Failed retries set `available_at` with exponential backoff
  (`JOB_RETRY_BACKOFF_SECONDS * 2^(n-1)`), so a worker cannot burn retries in a tight loop.

Tests written: process-death recovery, lease not yet expired, backoff blocks reclaim, retry
exhaustion, two concurrent workers, future `available_at` skipped, and rejected tags not recreated.
**Status:** not executed here (DB required); pure tagging tests pass.

## 10. Test, lint, type-check and build results (Phase 1 snapshot)

The final sprint numbers are in the banner at the top of this file. The table below records the
Phase 1 run; the OpenAPI count grew from 32 to 34 paths when the Trails endpoints were added.

Run from the repository root:

| Check | Command | Result |
|---|---|---|
| Ruff lint | `ruff check backend scripts` | `All checks passed!` |
| Ruff format | `ruff format --check backend scripts` | `69 files already formatted` |
| mypy | `mypy` | `Success: no issues found in 44 source files` |
| pytest | `pytest backend/tests -q` | `38 passed, 40 skipped in 1.14s` |
| OpenAPI | generated from `app.openapi()` | 32 paths written to `docs/openapi.json` |
| Frontend | not run in this session | unchanged by this phase |

The 40 skips are database tests. They require `TEST_DATABASE_URL` pointing at a database whose name
ends in `_test`; this machine has no PostgreSQL and no Docker. Therefore the acceptance criterion
"existing 48 backend tests still pass" is **not verified here**. The prior committed state reported
48 passing with a database; that claim is not reused as a current result.

## 11. Real-image CLIP check (not an accuracy metric)

Three dataset photos were scored with the revised prompt config. Top raw cosine scores:

| Image | Top scores |
|---|---|
| `adalaj-stepwell/ac645841a68d9a0a.jpg` | sculptural carvings 0.3048, carved pillars 0.2973, stone arches 0.2925 |
| `amber-fort/d2c60f13b6a7422d.jpg` | domes 0.2657, stone arches 0.2546, staircases 0.2403 |

With all committed thresholds `null`, `tag_image` returned `[]` for the Adalaj image. This shows the
no-forced-prediction path on real input. It says nothing about precision or recall.

## 12. Repository workflow

```bash
# 1. Database
docker compose up -d db
cp .env.example .env
python backend/scripts/init_db.py

# 2. Models (CPU only)
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r backend/requirements-ml.txt
set HF_HOME=C:\models\hf   # optional cache

# 3. Dataset
python backend/scripts/load_dataset.py
python backend/worker.py --once
python backend/scripts/embed_descriptions.py

# 4. Folder of new photos
python backend/scripts/ingest_folder.py "D:\photos\trip" --dry-run
python backend/scripts/ingest_folder.py "D:\photos\trip" --radius-m 300
python backend/worker.py

# 5. Tags and evaluation
python backend/scripts/eval_tagging.py --template   # fill by hand first
python backend/scripts/tune_tagging.py --write
python backend/scripts/eval_tagging.py
python backend/scripts/eval_fewshot.py
python backend/scripts/eval_search.py
python backend/scripts/eval_review_stats.py

# 6. Checks
ruff check backend scripts && ruff format --check backend scripts
mypy
pytest backend/tests -q
```

## 13. Status summary

| Item | Status |
|---|---|
| Site type removed from tagging | Implemented; unit-tested with synthetic vectors |
| Seven-label prompt config with 4 variants | Implemented; real-image scoring run |
| Per-label thresholds, no forced prediction | Implemented; unit-tested; no labels to tune yet |
| Negative-prompt comparison | Implemented; waiting for labels |
| Annotation template and site-wise split | Implemented; tested |
| Tagging metrics | **Not measured** (no human labels) |
| Few-shot probe | Implemented; **insufficient labels** |
| Self and same-site exclusion | Implemented; DB tests written, **not run** |
| Search metadata and provenance | Implemented; DB tests written, **not run** |
| EXIF scan, dedupe, clustering | Tested on 160 real files (dry-run) |
| Full folder ingestion to database | **Blocked** (no database) |
| Review URL, reviewer list, append-only | Implemented; DB tests written, **not run** |
| Job lease, retries, backoff, terminal failure | Implemented; DB tests written, **not run** |
| mypy, Ruff, CI | Pass locally; mypy added to CI |
| Frontend changes | None in this phase; integration contract documented |

## 14. Remaining defects and blockers

1. No human feature labels, so every tagging and few-shot metric is unavailable and all thresholds
   are `null`. The worker currently produces no automatic feature tags by design.
2. No PostgreSQL/pgvector or Docker in this environment: 40 database tests, full ingestion, real
   retrieval examples and real job-recovery runs are unverified here.
3. EXIF GPS coverage on the web-sourced dataset is 2/160; phone-photo coverage is unknown.
4. `max_per_site` is page-level only, not a global diversity guarantee.
5. Reviewer identity is a fixed demo list, not authentication; it can be impersonated.
6. The folder CLI and `GET /ingest/batches` are the only ingestion interfaces; there is no secure
   server-side folder picker, by design.
7. The site split leaves only ~4 held-out sites; even with labels, results are exploratory.
8. `scikit-learn` was added to `requirements-dev.txt` for the few-shot probe only; the API and
   worker do not depend on it.

## 15. Frontend integration requirements for Antigravity

No frontend file is changed. The backend now supplies:

- Search hits: existing fields plus `tags[]`, `author`, `licence`, `licence_url`, `source_url`.
  Render each tag with its `status`; never show `score` as a percentage or confidence.
- Image-to-image: add optional `cross_site` toggle, optional `max_per_site`, and pass
  `exclude_image_id` when the user searches with an already-indexed image. Default stays compatible.
- Review queue: display `url` (already `/files/...`), label, raw `score`, `model_name`,
  `model_version`, `prompt_version`, `author`, `licence`, `licence_url`, `source_url`.
- Reviewer picker: fetch `GET /review/reviewers` instead of free text; show that this is a demo
  audit label, not login.
- Draft sites: list `GET /sites/drafts`, allow rename via `PATCH /sites/{id}`, then confirm, reject
  or merge. Label them visibly as unverified clusters, never as confirmed monuments.
- Batch upload: `POST /images/upload-batch` returns per-file results and errors; show partial
  success.
- Ingest batches: `GET /ingest/batches` is read-only progress for CLI folder runs.

## 16. Recommended next task

Collect human feature labels on the tuning and test sites using
`python backend/scripts/eval_tagging.py --template`, then run `tune_tagging.py --write` and
`eval_tagging.py` against a real test database. That is the single step that turns the current
tagging system from "safe but silent" into a measured system, and it unblocks every other ML metric.

## 17. Phase 2A — Supabase verification (3 Nov 2026)

Status: **blocked before any database connection could be made.** No schema, data or credential
was changed, and no local PostgreSQL or Docker was installed.

### 17.1 Configuration inspected

| Item | Finding |
|---|---|
| `.env` `DATABASE_URL` | `localhost:5432`, database `atlas`, no query parameters. Not a Supabase host. |
| `TEST_DATABASE_URL` | Not set in `.env`, the shell environment or CI for this machine. |
| App DB layer | psycopg 3 (`psycopg[binary]`) with `pgvector.psycopg.register_vector`; no SQLAlchemy engine or session exists. |
| Migrations | No Alembic. Raw SQL: `db/schema.sql` plus `db/migrations/001_backend_expansion.sql` and `002_phase1.sql`, applied by `backend/scripts/init_db.py`. |
| CI database | GitHub Actions service `pgvector/pgvector:pg16` with `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/atlas_test`. |
| Supabase settings | None in the repo or `frontend/.env.local`. A prior Supabase CLI telemetry trace on this machine references one hosted project, but no access token or database password is configured. |

`.env` is gitignored; no credential is committed.

### 17.2 Connectivity attempt (no credential printed)

- Configured URL: `ConnectionTimeout: connection timeout expired` for `localhost:5432`
  (`::1` and `127.0.0.1`). TCP to `127.0.0.1:5432` is refused; no `postgres` process or service exists.
- Docker is not installed, so `docker compose up -d db` cannot be used.
- Supabase network reachability was checked without authenticating: the project's direct
  `db.<ref>.supabase.co` host resolved to IPv6 only, while the IPv4 pooler hosts resolved and
  accepted TCP on 5432 and 6543. No authenticated connection was attempted because no connection
  string or password is configured.
- pgvector availability: **not verified**. `db/schema.sql` starts with
  `CREATE EXTENSION IF NOT EXISTS vector`, and the CI image includes pgvector, but neither proves
  the hosted project has it.

### 17.3 Test isolation assessment

- No Supabase test project and no `*_test` database is configured.
- `backend/tests/conftest.py` refuses any URL whose database name does not end in `_test`, and its
  `clean_db` fixture truncates every table. Pointing it at the development project would be destructive.
- Schema-only isolation is not safe here: the app uses unqualified table names, `schema.sql` has
  unqualified DDL and `CREATE EXTENSION`, and `init_db.py --reset` hardcodes `public`.
- Recommended when credentials are available: a separate Supabase test project, or a separate
  `atlas_test` database inside it, reached through the **session pooler** (port 5432, IPv4) with
  `sslmode=require`. The transaction pooler is not recommended for schema setup and truncation.

### 17.4 Results

| Check | Result |
|---|---|
| `pytest backend/tests -q` | 43 passed, 45 skipped, 0 failed. The 45 skips are database tests because `TEST_DATABASE_URL` is unset. They are not reported as passed. |
| `ruff check backend scripts` | All checks passed |
| `ruff format --check backend scripts` | 71 files already formatted |
| `mypy` | Success: no issues found in 45 source files |
| Phase 1 DB behaviours (Step 5) | Not executed |
| Real-image smoke test against a database (Step 6) | Not executed |

### 17.5 What is needed to continue

Set `TEST_DATABASE_URL` to an isolated Supabase test database whose database name ends in `_test`,
using the session pooler with `sslmode=require`. Do not provide the development project URL.

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres.<ref>:<password>@<region>.pooler.supabase.com:5432/atlas_test?sslmode=require"
& backend\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The empty `atlas_test` database must exist before the first run. `conftest.py` applies
`db/schema.sql` and both migrations; `init_db.py` is not required. `CREATE EXTENSION vector` must be
permitted, or the extension must already be enabled.

## 18. Final stabilisation sprint (3 Nov 2026)

Scope: backend only. No frontend file was edited, no Git history was rewritten, and no database was
touched. The fixes below are covered by unit tests that run without a database; the API-level
regression tests are written and will run once `TEST_DATABASE_URL` is configured.

### 18.1 Fixes

| Fix | Behaviour |
|---|---|
| Malformed EXIF GPS | `_gps_coordinate` now catches bad rationals, non-finite values and out-of-range results and returns `None` instead of raising. |
| Blank human label | `HumanTagCreate.label` is stripped and rejected when empty (422). |
| Blank trail title | `TrailCreate`, `TrailUpdate` and `TrailFromImages` reject whitespace-only titles. |
| Blank search query | `/search/text` and `/search/images` return 400 for whitespace-only `q` instead of reaching the model and returning 500. |
| Database integrity errors | A `psycopg.errors.IntegrityError` now returns 409, not the generic 503. |
| Image-search upload | The upload is read with a `max_bytes + 1` bound, so an oversized file is rejected without buffering it all. |
| Trails update | `PATCH /trails/{id}` updates title, description or visibility. |
| Remove stop | `DELETE /trails/{id}/stops/{stop_id}` deletes the stop and renumbers the rest from 1. |
| Stop coordinates | `TrailStopOut` now includes `lat` and `lon` from the site. |
| Distance semantics | `TrailSummaryOut` states `distance_mode: "straight_line"` and lists `missing_coordinates`. |
| EXIF-derived trail | `POST /trails/from-images` groups stored photos by site, orders stops by earliest `captured_at`, and reports `images_used` / `images_skipped`. |
| Smoke test script | `backend/scripts/smoke_test.py` now accepts zero auto tags when thresholds are `null`, no longer expects site-type tags, asserts the query image is excluded from image-to-image results, and uses a configured reviewer plus a human-added tag when the review queue is empty. |

### 18.2 New tests

- `backend/tests/test_images_service.py`: malformed GPS rationals, infinity, out-of-range and wrong
  shape.
- `backend/tests/test_review_api.py`: blank human label rejected by the schema.
- `backend/tests/test_geo.py`: missing-coordinate reporting is unique and ordered.
- `backend/tests/test_trails_service.py`: visit grouping order and unusable-row skipping.
- `backend/tests/test_trails_api.py`: update, remove-stop renumbering, missing coordinates, empty
  summary, EXIF-derived trail and skipped-image counts.
- `backend/tests/test_search_api.py`: whitespace-only query returns 400.

### 18.3 Still blocked

- The 45 database tests, real ingestion into PostgreSQL, real search/review/worker runs and the
  Supabase checklist are unverified because no `TEST_DATABASE_URL` or Supabase credentials exist.
- Tagging metrics, threshold tuning and the logistic-regression probe remain blocked by the missing
  `data/dataset/tag_annotations.csv`; every threshold stays `null`.
