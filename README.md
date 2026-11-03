# Heritage Atlas

From fragmented heritage records to verified, explorable cultural journeys. HackCult '26, track
HC26-CULT01.

FastAPI + PostgreSQL/pgvector backend, CLIP and MiniLM embeddings, Wikimedia dataset pipeline, and
a Next.js/Leaflet frontend (owned by the frontend lane).

## Documentation
| File | Purpose |
|---|---|
| docs/PRD.md | Problem, users, scope, acceptance criteria, risks |
| docs/ARCHITECTURE.md | Components, embedding spaces, flows, scalability, limitations |
| docs/API.md | API contract (behaviour) |
| docs/api-contracts.md | Endpoint map for integration |
| docs/openapi.json | Generated OpenAPI schema |
| docs/FINAL_ENGINEERING_REPORT.md | Historical build snapshot (superseded; see SUBMISSION_READINESS) |
| docs/PHASE_1_ENGINEERING_REPORT.md | Phase 1 fixes: tagging, retrieval, ingestion, review, reliability |
| docs/SUBMISSION_READINESS.md | Current verified/unverified status, blockers and demo sequence |
| docs/DATASET.md | Data sourcing and licence rules |
| docs/EVALUATION.md | How results are measured |
| docs/TASKS.md | Task board by lane |
| docs/WORKFLOW.md | Working with multiple agents |
| db/schema.sql | Database schema (source of truth) |
| AGENTS.md | Rules for AI coding agents |

## Quick start (backend)
Prerequisites: Python 3.11+, Docker (for the database) or any PostgreSQL 15+ with pgvector.

    docker compose up -d db
    cp .env.example .env
    cd backend
    python -m venv .venv
    source .venv/bin/activate            # Windows: .venv\Scripts\activate
    pip install -r requirements-ml.txt   # core + CLIP/MiniLM
    python scripts/init_db.py
    uvicorn app.main:app --reload        # terminal 1
    python worker.py                     # terminal 2 (first run downloads the models)

`GET /health` reports the database and model state. Interactive docs: `http://localhost:8000/docs`.

Without Docker, point `DATABASE_URL` at any pgvector-enabled PostgreSQL and run
`python scripts/init_db.py`.

### Supabase / hosted PostgreSQL
Use the **session pooler** (IPv4, port 5432) for schema setup and for the test database. The
transaction pooler is not suitable for `CREATE EXTENSION`, DDL or the truncation used by tests.

    DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/postgres?sslmode=require
    TEST_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/atlas_test?sslmode=require

Checklist for the developer once the Supabase project exists:

1. Create an empty `atlas_test` database. Never point `TEST_DATABASE_URL` at the development
   database: the test guard only accepts names ending in `_test`, and the suite truncates tables.
2. Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;` (or confirm it is already available).
3. Apply the schema and migrations with `python backend/scripts/init_db.py`. It runs
   `db/schema.sql`, `db/migrations/001_backend_expansion.sql` and `db/migrations/002_phase1.sql`.
4. Run the database suite against the test database, then the smoke test against the app database:
   `python backend/scripts/smoke_test.py --help`.
5. Keep `sslmode=require`; never commit the password. `.env` is gitignored and `.env.example`
   contains placeholders only.

The Supabase connection has **not** been executed in this build; see
`docs/SUBMISSION_READINESS.md` for the exact blocked status.

### CORS, uploads and write endpoints
`CORS_ORIGINS` is a comma-separated allow-list (default `http://localhost:3000`). Uploads are
limited by `MAX_UPLOAD_MB` (default 15) and validated as JPEG, PNG or WebP. There is no user
authentication in the hackathon build; the reviewer list is a fixed audit label. Do not expose the
write endpoints publicly without adding an API key or real auth.

### CPU-only worker and model cache
No GPU is required. The worker and API use the same `requirements-ml.txt`:
PyTorch (CPU wheel), `sentence-transformers`, Pillow and NumPy. To keep the install small:

    pip install --index-url https://download.pytorch.org/whl/cpu torch
    pip install -r backend/requirements-ml.txt

The first run downloads `clip-ViT-B-32` and `all-MiniLM-L6-v2` into
`~/.cache/huggingface`. To prefetch them (or to ship them with the image), set a cache directory:

    set HF_HOME=C:\models\hf          # Windows
    export HF_HOME=/models/hf          # Linux/macOS
    python -c "from sentence_transformers import SentenceTransformer as S; S('clip-ViT-B-32'); S('all-MiniLM-L6-v2')"

An API-only process can run on `requirements.txt` alone; the heavy imports in `app/ml.py` are lazy,
so the API starts without torch. Only the worker (and query-time embedding) needs the ML stack.

## Dataset
The committed dataset has 30 Gujarat/Rajasthan sites and 150 Wikimedia images with author, licence,
licence URL, source URL and dimensions. Raw images are gitignored.

    python -m scripts.dataset.download_wikimedia   # downloads into data/raw (skips existing)
    python -m scripts.dataset.generate_metadata    # writes data/sites.csv + JSON manifests
    python -m scripts.dataset.validate_images      # dimensions, duplicates, metadata
    python -m scripts.dataset.generate_report      # data/dataset/REPORT.md

Outputs: `data/dataset/manifest.json`, `sites.json`, `images.json`, `validation.json`, `REPORT.md`.
`python -m scripts.dataset.download_roboflow` is optional and skips cleanly without credentials.

Load and embed the dataset:

    python backend/scripts/load_dataset.py
    python backend/worker.py --once
    python backend/scripts/embed_descriptions.py

## Folder ingestion (EXIF GPS)
Ingest a local trip folder as draft sites. `--dry-run` scans, hashes and clusters without touching
the database, which is the safest way to check EXIF coverage first:

    python backend/scripts/ingest_folder.py "D:\photos\trip" --dry-run
    python backend/scripts/ingest_folder.py "D:\photos\trip" --radius-m 300 --author "unknown"

Progress is available at `GET /ingest/batches/{id}`. Draft clusters appear at `GET /sites/drafts`
and are confirmed, renamed, merged or rejected through the API; they are never treated as verified
monuments. Missing attribution is stored as `unknown`, never invented.

## Explorer Trails
Create a trail, add sites as stops, reorder or remove them, and read the route summary:

    POST   /trails                      {"title","description","created_by","is_public"}
    GET    /trails                      ?created_by=&is_public=&limit=&offset=
    GET    /trails/{id}
    PATCH  /trails/{id}                 {"title","description","is_public"} (any subset)
    POST   /trails/{id}/stops           {"site_id","visit_date","note"}
    DELETE /trails/{id}/stops/{stop_id}
    PATCH  /trails/{id}/stops/reorder   {"stop_ids":[...]}
    POST   /trails/from-images          {"title","image_ids":null}
    GET    /trails/{id}/summary
    GET    /trails/{id}/journal

`/trails/from-images` groups stored photographs into one stop per site and orders them by the
earliest EXIF `captured_at`. Images without a capture time or site coordinates are skipped and
counted. Route legs use the Haversine great-circle formula: `distance_mode` is always
`"straight_line"`, never road distance. `missing_coordinates` lists sites that cannot be measured.
The generated journal is template-based and keeps `original_note` separate from
`generated_summary`.

## End-to-end checkpoint
    python backend/scripts/checkpoint.py

Uploads a cropped dataset photo, drains the worker, then exercises text search, text-to-image,
image-to-image, related sites, review and trails. Results: `data/dataset/checkpoint.json`.

## Evaluation
Numbers are reported only from hand labels; the scripts refuse to invent them.

    python backend/scripts/eval_tagging.py --template   # empty annotation sheet
    python backend/scripts/tune_tagging.py --write      # per-label thresholds on tuning sites only
    python backend/scripts/eval_tagging.py              # baseline vs revised vs negatives, test sites
    python backend/scripts/eval_fewshot.py              # logistic probe vs zero-shot on identical sites
    python backend/scripts/eval_search.py               # precision@5 + latency
    python backend/scripts/eval_review_stats.py         # review counts by tag

## Tests, lint and types
    ruff check backend scripts && ruff format --check backend scripts
    mypy                                 # configured in pyproject.toml, run from the repo root
    pytest backend/tests -q

Database tests need `TEST_DATABASE_URL` pointing at a database whose name ends in `_test`:

    TEST_DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas_test pytest backend/tests -q

## Layout
    backend/app/            FastAPI app: routers, repositories, services, ml, schemas
    backend/worker.py       DB-backed job worker (idempotent, retries)
    backend/scripts/        init, dataset loader, embeddings, checkpoint, evaluation
    backend/tests/          unit and API tests
    db/schema.sql           schema; db/migrations/ for upgrades
    scripts/dataset/        Wikimedia/Roboflow pipeline
    data/dataset/           committed manifests, validation and reports
    frontend/               Next.js app (separate lane)

## Design rules
- CLIP (512-d) and MiniLM (384-d) are separate spaces; never compare across them.
- Tag scores are raw cosine similarities, not probabilities. Per-label thresholds live in
  `backend/app/feature_prompts.json`; `null` means the feature is never emitted.
- AI never overwrites original notes; every review is appended to `tag_reviews`.
- Licence and author are stored per image.
- Heavy ML runs in the worker; only a single query embedding runs in a request.
