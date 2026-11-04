# Heritage Atlas

**HackCult '26 — Track HC26-CULT01: Digital Revitalisation of Unstructured Cultural & Architectural
Heritage Archives**

Heritage Atlas turns scattered heritage field documentation — photographs, notes, coordinates,
authors and licences — into a searchable, map-based archive with AI-assisted discovery and an
explicit human-verification layer. It is a FastAPI + PostgreSQL/pgvector backend with CLIP and
MiniLM embeddings, an optional retrieval-grounded Gemini assistant, and a Next.js + Leaflet
frontend.

> **Project status:** working hackathon build. All AI output is labelled as a suggestion; automatic
> feature tagging currently emits nothing because its per-label thresholds are still `null` pending
> human-labelled tuning data. Database-backed flows are implemented and covered by tests that need a
> PostgreSQL `_test` database. Read [Responsible AI and limitations](#responsible-ai-and-limitations)
> before quoting any capability.

## Contents

- [Overview](#overview)
- [Problem statement](#problem-statement)
- [Solution and features](#solution-and-features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [External APIs and data sources](#external-apis-and-data-sources)
- [Database schema](#database-schema)
- [Installation and setup](#installation-and-setup)
- [API reference](#api-reference)
- [Dataset and provenance](#dataset-and-provenance)
- [Responsible AI and limitations](#responsible-ai-and-limitations)
- [Testing and evaluation](#testing-and-evaluation)
- [Scalability and roadmap](#scalability-and-roadmap)
- [Repository structure](#repository-structure)
- [Documentation](#documentation)

## Overview

Heritage Atlas is built for three kinds of users:

| User | Need | How the platform helps |
|---|---|---|
| Field researcher / Explorer Fellow | Capture photos and notes quickly, then make sense of a trip | Upload with attribution and coordinates, asynchronous processing, trails built from photo timestamps |
| Heritage reviewer / archivist | Check machine suggestions without losing the original record | Review queue, confirm / reject / add tags, append-only audit history, original notes never overwritten |
| Visitor, student or researcher | Find heritage sites and photographs without knowing exact keywords | Semantic text search, visual similarity, map exploration and related-site discovery |

What makes it different from a plain image gallery:

1. **Provenance is a first-class concept.** Every tag carries `auto`, `verified`, `rejected` or
   `added_by_human`, and every decision is appended to `tag_reviews`. Original text, author and
   licence are stored per record and never replaced by AI output.
2. **Two purpose-built embedding spaces.** CLIP handles images and visual queries; MiniLM handles
   site descriptions. They are stored separately and never compared with each other.
3. **Discovery grounded in real records.** The optional assistant answers from retrieved database
   rows and returns the source records it used; it is not a free-form generator over an
   unverified corpus.
4. **Explorer Trails.** A trip becomes an ordered, mappable itinerary with honest straight-line
   distances and a template-generated journal that keeps the researcher's own note intact.

At a glance: 30 heritage sites, 150 curated images, two embedding spaces, 39 documented API paths,
six user-facing frontend routes.

## Problem statement

Heritage documentation is produced by many people and then scattered. A field researcher may have
photographs in a phone backup, notes in a document, coordinates in a separate spreadsheet, and
licence information in an email. The result is a corpus that is hard to search, hard to verify and
hard to reuse.

Concretely:

- **Fragmented information.** Sites, images, notes and coordinates live in different formats and
  locations, with no shared identifier.
- **Weak discovery.** Keyword search cannot answer "carved pillars inside a stepwell" when the
  record never used those words. Visual similarity is impossible with filenames alone.
- **Inconsistent metadata and attribution.** Author, licence, source and capture date are often
  missing, copied incorrectly or attached to the wrong file.
- **No trust boundary.** AI-generated labels look identical to human-checked facts unless the
  interface and schema keep them apart.
- **Limited review.** Without an audit trail, there is no way to know who confirmed or rejected a
  suggestion, or why.

The platform addresses these problems with a single schema, a provenance layer, two complementary
retrieval models, and a review workflow that treats AI as a proposal rather than a fact.

## Solution and features

Status legend:

- **Implemented** — code exists and the non-database tests in this repository run locally.
- **Implemented, needs PostgreSQL** — the endpoint is covered by database tests that require
  `TEST_DATABASE_URL`; 45 such tests are skipped locally when no database is available (CI provides
  a pgvector service).
- **Optional** — off by default; requires configuration or credentials.
- **Not implemented** — explicitly out of scope for this build.

| Feature | What it does | Technology | Status |
|---|---|---|---|
| Heritage archive and gallery | Stores sites and images with notes, coordinates, author, licence and source; renders a site page with a photo gallery | FastAPI, PostgreSQL, Next.js | Implemented, needs PostgreSQL |
| Interactive map | Plots sites as pins, clusters them, filters by region/category/verified content, flies to a site | Leaflet, `leaflet.markercluster` | Implemented |
| Semantic text search | Ranks sites by meaning of their descriptions | MiniLM (`all-MiniLM-L6-v2`, 384-d), pgvector | Implemented, needs PostgreSQL |
| Visual search and text-to-image | Finds photographs that look like a query photo or match a written description | CLIP (`clip-ViT-B-32`, 512-d), pgvector HNSW | Implemented, needs PostgreSQL |
| Related sites | Suggests nearby-in-meaning sites using image similarity plus tag overlap, with evidence | CLIP + Jaccard fusion | Implemented, needs PostgreSQL |
| Ask Heritage Atlas | Answers questions from retrieved records, with source records and fallback text | Google Gemini via `google-genai`, optional | Optional |
| AI feature suggestions | Proposes architectural features from a fixed vocabulary using zero-shot prompts | CLIP prompt ensembles, `heritage-v2` | Implemented, **currently emits no tags** (thresholds `null`) |
| Upload and background processing | Accepts photos with metadata, deduplicates by SHA-256, queues a job, embeds asynchronously | FastAPI, database job queue, Python worker | Implemented, needs PostgreSQL |
| Batch upload | Accepts several files and reports per-file success or failure | `POST /images/upload-batch` | Implemented (API); the UI uploads one file per request |
| Folder ingestion | Scans a local folder, reads EXIF GPS/time, clusters points, creates draft sites | `ingest_folder.py`, Pillow, Haversine clustering | Implemented; dry run verified |
| Explorer Trails | Ordered stops, reorder/remove, straight-line distance summary, journal from photos | FastAPI, Haversine, template journal | Implemented, needs PostgreSQL |
| Human review | Queue of suggestions; confirm, reject or add a tag; append-only history | `image_tags`, `tag_reviews`, review UI | Implemented, needs PostgreSQL |
| Attribution and licence provenance | Stores and displays author, licence, licence URL and source URL per image | PostgreSQL, frontend provenance chips | Implemented |
| Users and authentication | Minimal reviewer records only | `users` table | **Authentication not implemented** |

### Heritage archive and site pages

`GET /sites/{id}` returns a site with its images and tags. The frontend site page shows the original
description (never AI-edited), the image gallery with native aspect ratios, per-image author and
licence, tag chips with provenance, and a related-sites section. If related sites fail to load, the
main page still renders.

### Interactive map

The homepage renders all sites on a Leaflet map with marker clustering, region and category
filters, a selected-site preview panel, and a keyboard-accessible site list. Map tiles come from
OpenStreetMap. A separate location picker is used on the upload page so coordinates can be corrected
by hand.

### Semantic text search (MiniLM)

`GET /search/text?q=...` embeds the query with `all-MiniLM-L6-v2` (384 dimensions) and compares it
with stored site-description vectors using cosine similarity. Filters for region, category, tag,
verified content, site and pagination are applied in SQL. A blank query returns `400`.

### Visual and text-to-image search (CLIP)

- `GET /search/images?q=...` encodes the text with CLIP's text encoder and searches the 512-d image
  vectors.
- `POST /search/by-image` encodes an uploaded photo and returns visually similar stored photos. The
  query photo's own SHA-256 match is excluded, and optional `cross_site`, `exclude_image_id` and
  `max_per_site` parameters control discovery mode and diversity.

Results include the image URL, site name, raw cosine score, active tags and full attribution.

### Related sites

`GET /sites/{id}/related` combines the mean CLIP similarity of the two sites' images with the Jaccard
overlap of their active tags:

```
score = alpha * mean_CLIP_similarity + (1 - alpha) * tag_Jaccard
```

`alpha` defaults to `RELATED_CLIP_WEIGHT=0.6` and can be overridden per request. The response
includes the component scores, shared tags and the nearest image pair so the reason is inspectable.

### Ask Heritage Atlas (Gemini)

`POST /ai/chat` retrieves candidates first: the requested site or image if given, otherwise MiniLM
site search and, for visual questions, CLIP image search. Only the retrieved rows are placed in a
delimited `<retrieved_records>` block and sent to Gemini with a strict system instruction: use only
those records, never invent dates/authors/features, and keep original attribution distinct from AI
interpretation.

The response carries `ai_generated`, an intent label, the source records and any warnings. If the
provider is disabled, rate-limited or fails, the endpoint returns a deterministic fallback built
from the retrieved records instead of failing the request.

Related endpoints: `GET /ai/status`, `POST /ai/explain/{site_id}`, `POST /ai/trails/suggest`. The
trail-suggestion endpoint is implemented in the API; the current frontend does not call it.

### AI feature suggestions

The worker scores each image against seven architectural feature labels — sculptural carvings,
jali work, staircases, domes, stone arches, carved pillars, decorative brackets — using four CLIP
prompt variants per label, averaged and renormalised. Optional negative prompts exist for tuning.
Accepted labels are capped at `MAX_FEATURES` (default 4).

A feature is accepted only when its raw cosine similarity reaches that label's own threshold.
**All seven thresholds are currently `null`, so the worker emits no automatic feature tags.** An
empty tag list is the intended safe outcome, not a bug. Site type is never predicted; the site record
owns its category.

### Upload and background ingestion

`POST /images/upload` accepts a multipart photo plus a site (existing or new) and optional metadata,
stores the file, inserts an `images` row and a `jobs` row, and returns `202` with the job id.
Validation covers MIME/format (JPEG, PNG, WebP), size (`MAX_UPLOAD_MB`), and SHA-256 deduplication.
Duplicate content returns the existing image with `duplicate: true`.

The worker claims jobs with `FOR UPDATE SKIP LOCKED`, computes the CLIP embedding, writes
auto-suggested tags with model and prompt provenance, and embeds the site description with MiniLM.
Failures are retried with exponential backoff up to `JOB_MAX_RETRIES`; a stale lease is recovered.
Re-processing replaces only `auto` tags, so human decisions survive. The original file and notes are
never deleted.

### Folder ingestion

`ingest_folder.py` is for local trip folders that a browser cannot address. It scans recursively,
validates and hashes files, reads EXIF GPS and capture time, clusters GPS points within a radius
(default 300 m), and creates **draft** sites plus processing jobs. Files without GPS go to a separate
draft bucket. Drafts are never treated as verified monuments: a reviewer confirms, renames, merges or
rejects them through the API. A `--dry-run` mode performs no database writes.

### Explorer Trails

A trail is an ordered list of stops. The API supports creating trails, adding, removing and
reordering stops, and building a trail from stored photographs (`POST /trails/from-images`), where
each usable photo contributes one stop per site ordered by the earliest EXIF capture time.

`GET /trails/{id}/summary` returns legs and a total using the Haversine great-circle formula.
`distance_mode` is always `straight_line`; sites without coordinates are listed in
`missing_coordinates` and excluded. `GET /trails/{id}/journal` produces a template-based journal
that keeps `original_note` and `generated_summary` in separate fields.

The frontend provides a trail list, a map with ordered stops, a summary panel and a journal view.

### Human review and provenance

The review queue (`GET /review/queue`) lists suggestions ordered by lowest raw score, with the image
URL and full provenance. A reviewer can confirm, reject or add a tag. Each action appends a row to
`tag_reviews`; history is never rewritten. Reviewer identifiers come from the `REVIEWERS`
environment variable and are **audit labels, not authentication**.

The UI uses the same chip vocabulary everywhere: suggested (sparkle), verified (check), added
(person) and rejected (cross), with the raw score shown as a number, never as a percentage.

## Architecture

### System overview

```mermaid
flowchart LR
    FE["Next.js 16 frontend<br/>App Router · TypeScript · Leaflet"]
    API["FastAPI service<br/>routers · repositories · validation"]
    QE["Query-time embedding<br/>one text string or one photo"]
    DB[("PostgreSQL 16<br/>+ pgvector<br/>HNSW cosine indexes")]
    WK["Background worker<br/>database job queue"]
    CLIP["CLIP ViT-B/32<br/>512-d image space"]
    MINI["MiniLM-L6-v2<br/>384-d text space"]
    GEM["Google Gemini API<br/>optional assistant"]
    WM["Wikimedia Commons<br/>dataset pipeline"]
    LOAD["load_dataset.py<br/>manifest validation"]

    FE -->|"REST / JSON"| API
    API --> QE
    QE --> CLIP
    QE --> MINI
    API --> DB
    API -.->|"grounded prompt"| GEM
    WK --> DB
    WK --> CLIP
    WK --> MINI
    WM --> LOAD
    LOAD -->|"sites, images, provenance"| DB
```

| Component | Responsibility |
|---|---|
| Next.js frontend | Map, site pages, search, upload, review, trails, assistant UI |
| FastAPI API | HTTP contract, validation, SQL queries, one query embedding per search request |
| Worker | Image embedding, zero-shot tagging, description embedding, retries and leases |
| PostgreSQL + pgvector | Canonical records, provenance, jobs, trails and both vector spaces |
| CLIP / MiniLM | Visual and textual representation, loaded lazily in worker and API |
| Gemini (optional) | Natural-language interpretation of retrieved records only |

### Image ingestion pipeline

```mermaid
flowchart TD
    UP["Browser upload<br/>/images/upload · /images/upload-batch"]
    FOLDER["Local folder ingestion<br/>ingest_folder.py"]
    VAL["Validate input<br/>JPEG/PNG/WebP · size limit · SHA-256 dedupe<br/>author, licence, source recorded or 'unknown'"]
    ROW["Write site, image and job rows<br/>image status = uploaded"]
    QUEUE[("jobs table<br/>pending · lease · retry · backoff")]
    WK["Worker claims one job<br/>FOR UPDATE SKIP LOCKED"]
    PROC["Decode image + apply EXIF orientation"]
    EMB["CLIP image embedding (512-d)<br/>zero-shot feature scores"]
    TXT["MiniLM description embedding (384-d)"]
    STORE[("images.clip_embedding<br/>image_tags (status = auto)<br/>sites.description_embedding")]
    SEARCH["Search, related sites, review queue"]

    UP --> VAL
    FOLDER --> VAL
    VAL --> ROW --> QUEUE --> WK --> PROC
    PROC --> EMB --> STORE
    PROC --> TXT --> STORE
    STORE --> SEARCH
    WK -.->|"failure: retry with backoff; upload kept"| QUEUE
```

### Discovery and review flows

```mermaid
flowchart TD
    Q["User question, phrase or photo"]
    CLIPQ["CLIP text or image encoder<br/>512-d query vector"]
    MINIQ["MiniLM text encoder<br/>384-d query vector"]
    CLIPDB[("images.clip_embedding<br/>cosine similarity")]
    MINIDB[("sites.description_embedding<br/>cosine similarity")]
    RES["Ranked results with score and provenance"]
    GEMQ["Gemini assistant<br/>retrieved rows only"]
    ANS["AI interpretation<br/>ai_generated + source records"]
    REV["Human review<br/>confirm · reject · add"]
    AUDIT[("tag_reviews<br/>append-only")]
    ACTIVE["Active tag status<br/>verified · rejected · added_by_human"]

    Q --> CLIPQ --> CLIPDB
    Q --> MINIQ --> MINIDB
    CLIPDB --> RES
    MINIDB --> RES
    MINIDB -.->|"top sites as context"| GEMQ
    CLIPDB -.->|"top photos as context"| GEMQ
    GEMQ --> ANS
    RES --> REV --> AUDIT
    REV --> ACTIVE
```

### Embedding spaces (critical)

| Space | Model | Dimensions | Stored in | Used for |
|---|---|---|---|---|
| CLIP | `clip-ViT-B-32` via `sentence-transformers` | 512 | `images.clip_embedding` | Image-to-image, text-to-image, zero-shot feature scores, related sites |
| MiniLM | `all-MiniLM-L6-v2` via `sentence-transformers` | 384 | `sites.description_embedding` | Semantic text search over site descriptions |

**CLIP and MiniLM vectors are never compared.** They are different models with different dimensions
and different training objectives; a cosine between them is meaningless. If results from both spaces
must be merged, use rank-based fusion (for example reciprocal rank fusion), not raw scores. Each
model's output dimension is checked when it loads, and a mismatch raises `ModelDimensionError` instead
of producing vectors that do not fit the schema.

### Frontend performance note

The homepage hero image is rendered with Next.js `<Image priority>` (`fill`, `sizes="100vw"`,
`quality={90}`), so the above-the-fold LCP asset is fetched at high priority and served as optimised
WebP instead of an unoptimised plain image. The container already defines the hero box, so `fill`
reserves space and adds no layout shift. `next.config.ts` allows the `quality={90}` value and permits
optimising the `localhost:8000` dev backend with `dangerouslyAllowLocalIP` **in development only**
(it is `false` in production); `remotePatterns` still restricts fetches to `localhost:8000`.

The hero URL comes from the sites API, so the image cannot begin downloading before those calls
resolve; the heading and CTA are static and render immediately. Runtime behaviour was verified
against a local mock API: the browser requested the hero through `/_next/image` and received
`200 image/webp`. No quantitative LCP or timing improvement is claimed.

## Technology stack

Only libraries that are imported or configured by this repository are listed. Versions come from
`frontend/package.json`, `frontend/package-lock.json` and `backend/requirements*.txt`.

### Frontend

| Library | Version | Purpose |
|---|---|---|
| Next.js | 16.4.3 | App Router, routing, server build, image optimisation |
| React / React DOM | 19.3.0 | Component model and rendering |
| TypeScript | ^5 | Strict typing across the app |
| Tailwind CSS | ^4 (via `@tailwindcss/turbopack`) | Design tokens and utility styling |
| Leaflet | 1.9.4 | Interactive maps |
| `leaflet.markercluster` | 1.5.3 | Marker clustering on the explore map |
| `@types/leaflet`, `@types/leaflet.markercluster` | ^1.9.22 / ^1.5.6 | Type definitions for Leaflet |
| Vitest | ^5.0.5 | Unit tests for pure helpers and API formatting |
| ESLint + `eslint-config-next` | ^9 / 16.4.3 | Linting |
| `@types/node`, `@types/react`, `@types/react-dom` | ^24 / ^19 / ^19 | Type definitions |

All API access goes through `frontend/lib/api.ts`. `NEXT_PUBLIC_USE_MOCKS` exists only for offline UI
work; the default is `false` so the app talks to the real API.

### Backend

| Library | Purpose |
|---|---|
| Python 3.11+ | Runtime |
| FastAPI | HTTP API, validation, OpenAPI generation |
| Uvicorn (`uvicorn[standard]`) | ASGI server |
| `python-multipart` | Multipart photo uploads |
| `psycopg[binary]` (Psycopg 3) | PostgreSQL driver, raw parameterised SQL |
| `pgvector` | Python adapter for vector columns |
| NumPy | Embedding math, cosine and mean vectors |
| Pillow | Image decoding, EXIF orientation, format validation |
| `python-dotenv` | Environment loading from `.env` |
| `google-genai` | Official Google GenAI SDK used by the optional Gemini provider |

### Database and vector search

| Component | Purpose |
|---|---|
| PostgreSQL 16 | Relational store for sites, images, tags, reviews, jobs, trails |
| pgvector | `vector(512)` and `vector(384)` columns plus HNSW cosine indexes |
| `docker compose` (`pgvector/pgvector:pg16`) | Reproducible local database with pgvector preinstalled |

### AI and machine learning

| Model / technique | Purpose |
|---|---|
| `clip-ViT-B-32` (Sentence Transformers) | 512-d image and text embeddings for visual search, tagging and related sites |
| `all-MiniLM-L6-v2` (Sentence Transformers) | 384-d description embeddings for semantic site search |
| Zero-shot prompt ensembles (`backend/app/feature_prompts.json`, `heritage-v2`) | Feature suggestions from four prompt variants per label, with per-label cosine cut-offs |
| Cosine similarity | The only score used within a single embedding space |
| Jaccard similarity | Tag overlap component of related-site ranking |
| Haversine formula | Straight-line trail distances |
| Google Gemini Flash (`gemini-3-flash-preview` by default) | Optional grounded assistant; model is configurable via `GEMINI_MODEL` |
| scikit-learn | Evaluation-only logistic-regression probe; not used by the API or worker |

### Development and testing tools

| Tool | Purpose |
|---|---|
| pytest | Backend unit and API tests |
| httpx | Test client transport for FastAPI |
| ruff | Backend lint and formatting |
| mypy | Static typing for backend and scripts |
| Vitest | Frontend unit tests |
| ESLint | Frontend lint |
| GitHub Actions | CI: backend lint/types/tests with a pgvector service, frontend lint/test/build |
| Git LFS | Stores the 150 curated dataset images |

## External APIs and data sources

| Service or source | Purpose | Notes |
|---|---|---|
| Wikimedia Commons (MediaWiki API) | Download curated heritage photographs, plus author, licence, licence URL, source URL and dimensions | Used by `scripts/dataset/download_wikimedia.py`; the delivered dataset is 150 images from Commons |
| Wikipedia / Wikidata | Site descriptions and source attribution | 26 site descriptions come from Wikipedia extracts and 4 from Wikidata; the source URL is stored per site |
| Google Gemini API | Optional conversational assistant and site explanation | Server-side only. Default model `gemini-3-flash-preview`, configurable. Disabled unless `AI_ENABLED=true` and `GEMINI_API_KEY` is set. Live calls were not exercised in this build environment |
| OpenStreetMap tile servers | Basemap tiles for Leaflet maps | Public tile usage; no key required |
| Roboflow | Optional additional dataset source | Skipped cleanly unless credentials are configured; not used by the committed dataset |
| Backend REST API | Internal contract between frontend and backend | Base URL from `NEXT_PUBLIC_API_URL`; OpenAPI at `/docs` |

No API keys or credentials are committed. `.env` is gitignored; `.env.example` contains placeholder
credentials and a sample hosted database host, and both must be replaced locally. The Gemini key, if
used, is read only on the server and is never sent to the browser.

## Database schema

Source of truth: [`db/schema.sql`](db/schema.sql). Upgrades are idempotent SQL files in
[`db/migrations/`](db/migrations), applied by `backend/scripts/init_db.py`, which also enables row
level security on every table for hosted deployments.

### Entity relationships

```mermaid
erDiagram
    users ||--o{ tag_reviews : "reviewer (optional)"
    sites ||--o{ images : "contains"
    sites ||--o{ trail_stops : "visited at"
    sites ||--o{ sites : "merged into"
    images ||--o{ image_tags : "has"
    tags ||--o{ image_tags : "labels"
    image_tags ||--o{ tag_reviews : "audited by"
    images ||--o{ jobs : "queued for"
    trails ||--o{ trail_stops : "ordered stops"

    sites {
        int id PK
        text name
        text region
        text category
        float lat
        float lon
        text description "original note, never AI-overwritten"
        text description_source
        vector description_embedding "MiniLM 384-d"
        text status "canonical | draft | rejected | merged"
        int merged_into_site_id FK
    }

    images {
        int id PK
        int site_id FK
        text storage_path
        text author
        text licence
        text licence_url
        text source_url
        text sha256 UK
        int width
        int height
        timestamptz captured_at
        jsonb exif
        vector clip_embedding "CLIP 512-d"
        text status "uploaded | processing | processed | failed"
    }

    tags {
        int id PK
        text label UK
        text tag_type "site_type | feature"
    }

    image_tags {
        int id PK
        int image_id FK
        int tag_id FK
        real score "raw cosine, not a probability"
        text status "auto | verified | rejected | added_by_human"
        text model_name
        text prompt_version
    }

    tag_reviews {
        int id PK
        int image_tag_id FK
        text reviewer
        int reviewer_id FK
        text action "confirm | reject | add"
        text previous_status
        text new_status
    }

    jobs {
        int id PK
        int image_id FK
        text status "pending | running | done | failed"
        int retry_count
        timestamptz claimed_at
        text worker_id
        timestamptz available_at
    }

    trails {
        int id PK
        text title
        text description
        text created_by
        bool is_public
    }

    trail_stops {
        int id PK
        int trail_id FK
        int site_id FK
        int stop_order
        date visit_date
        text note "original field note"
    }

    ingest_batches {
        int id PK
        text source_path
        text status
        int total_files
        int accepted
        int duplicates
        int gps_images
        jsonb report
    }
```

### How pgvector stores embeddings

- `images.clip_embedding` is `vector(512)`, written by the worker after CLIP encoding.
- `sites.description_embedding` is `vector(384)`, written by the worker (or
  `embed_descriptions.py`) after MiniLM encoding.
- Both columns have HNSW indexes with `vector_cosine_ops`, so nearest-neighbour queries stay fast as
  the archive grows.
- The two columns have different dimensions and are queried by different endpoints. No SQL joins or
  score fusion compares one column with the other.
- Tag scores in `image_tags.score` are raw cosine similarities in `[-1, 1]`; the schema comment and
  the UI both state that they are not probabilities.

## Installation and setup

These steps reproduce the development environment from a fresh clone. Commands are given for
Windows PowerShell and for Linux/macOS where they differ. Every command block states its working
directory.

### Prerequisites

| Requirement | Version / notes |
|---|---|
| Python | 3.11 or newer (the project targets 3.11) |
| Node.js | 22 LTS or newer (CI uses 22) |
| PostgreSQL | 16 with pgvector, or Docker Desktop with Compose |
| Git | With Git LFS installed |
| Disk space | Room for the Python/Node dependencies, the 114.3 MB image set and two Sentence Transformers models |
| GPU | Not required; CPU inference is supported |

### 1. Clone the repository

```bash
git clone https://github.com/Shivam-k3/Heritage-Atlas.git
cd Heritage-Atlas
git lfs install
git lfs pull
```

The 150 dataset images are stored with Git LFS. Without `git lfs pull` they are pointer files and
`load_dataset.py` will fail its SHA-256 check with a clear error.

### 2. Start PostgreSQL with pgvector

```bash
docker compose up -d db
```

This starts `pgvector/pgvector:pg16` on port 5432 with user `atlas`, password `atlas` and database
`atlas`. Without Docker, use any PostgreSQL 16 instance where `CREATE EXTENSION vector;` is
available, and point `DATABASE_URL` at it.

### 3. Configure environment variables

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Edit `.env` and set the database URL. For the Compose service above, use the value below. If you
copied `.env.example`, replace its sample hosted URL with this local value:

```dotenv
DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas
UPLOAD_DIR=./uploads
CORS_ORIGINS=http://localhost:3000
MAX_UPLOAD_MB=15

# Optional assistant: leave disabled unless you have a server-side key.
AI_ENABLED=false
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3-flash-preview
```

Never commit the real `.env`. For a hosted database, use `sslmode=require` and URL-encode special
characters in the password.

### 4. Create the backend virtual environment

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

### 5. Install backend dependencies

From `backend/` with the virtual environment active:

```bash
pip install --upgrade pip
pip install -r requirements-ml.txt
```

`requirements-ml.txt` includes the API requirements plus `sentence-transformers`. For tests and
linters, install `requirements-dev.txt` instead; it includes the API requirements but not the ML
stack.

CPU-only PyTorch keeps the install small:

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements-ml.txt
```

### 6. Initialise the database

From the repository root (the script loads `.env` and applies the schema, both migrations and row
level security):

```bash
python backend/scripts/init_db.py
```

`--reset` drops and recreates the public schema. Use it only against a disposable development
database.

### 7. Load and embed the curated dataset

From the repository root:

```bash
python backend/scripts/load_dataset.py
python backend/worker.py --once
python backend/scripts/embed_descriptions.py
```

- `load_dataset.py` validates the manifest (site uniqueness, SHA-256 of every image) and inserts
  sites, images and processing jobs. It is idempotent for existing hashes.
- `worker.py --once` drains the queued jobs. The first run downloads the CLIP and MiniLM models, so
  it takes noticeably longer than later runs on CPU.
- `embed_descriptions.py` backfills any site descriptions the worker did not embed.

### 8. Start the backend API

From `backend/`, with the virtual environment active:

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive documentation is served at `http://localhost:8000/docs` and the generated schema at
`http://localhost:8000/openapi.json`.

### 9. Start the background worker

In a second terminal, from `backend/`:

```bash
python worker.py
```

The worker keeps polling the `jobs` table. Stop it with `Ctrl+C`. Multiple workers can run safely
because claims use `FOR UPDATE SKIP LOCKED`.

### 10. Install and start the frontend

In a third terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

`frontend/.env.example` contains:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

Open `http://localhost:3000`.

### Verify the installation

| Check | Command | Expected |
|---|---|---|
| API health | `curl http://localhost:8000/health` | `{"status":"ok","database":"ok","models":{...}}` (503 if the database is down) |
| Readiness | `curl http://localhost:8000/readiness` | `{"status":"ready",...}` when both models and the database are available |
| Sites loaded | `curl http://localhost:8000/sites` | A non-empty JSON array after the dataset load |
| Swagger UI | Open `http://localhost:8000/docs` | All endpoint groups |
| Frontend | Open `http://localhost:3000` | Map with site pins, hero section and assistant |
| Frontend build | `cd frontend; npm run build` | Production build succeeds |

On Windows, `Invoke-RestMethod http://localhost:8000/health` is the PowerShell equivalent of `curl`.

### Optional: hosted PostgreSQL (Supabase)

Use the **session pooler** (IPv4, port 5432) for schema setup and for the test database. The
transaction pooler is not suitable for `CREATE EXTENSION`, DDL or the truncation used by tests.

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/postgres?sslmode=require
TEST_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/atlas_test?sslmode=require
```

Checklist:

1. Create an empty database whose name ends in `_test` for the suite. The test guard only accepts
   such names, and the suite truncates tables. Never point `TEST_DATABASE_URL` at the development
   database.
2. Enable pgvector with `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Apply the schema and migrations with `python backend/scripts/init_db.py`.
4. Run the database tests, then the smoke test:
   `python backend/scripts/smoke_test.py --help`.
5. Keep `sslmode=require`; keep the password local.

### Optional: model cache and CPU-only installs

The models are downloaded on first use into `~/.cache/huggingface`. To prefetch them or share a
cache:

```powershell
$env:HF_HOME = "C:\models\hf"
python -c "from sentence_transformers import SentenceTransformer as S; S('clip-ViT-B-32'); S('all-MiniLM-L6-v2')"
```

```bash
export HF_HOME=/models/hf
python -c "from sentence_transformers import SentenceTransformer as S; S('clip-ViT-B-32'); S('all-MiniLM-L6-v2')"
```

The API can run on `requirements.txt` alone: heavy imports in `app/ml.py` are lazy, so the server
starts without PyTorch. Only the worker and query-time embedding need the ML stack.

### Optional: folder ingestion

```bash
python backend/scripts/ingest_folder.py "D:\photos\trip" --dry-run
python backend/scripts/ingest_folder.py "D:\photos\trip" --radius-m 300 --author "unknown"
```

Progress is available at `GET /ingest/batches/{id}`. Draft clusters appear at `GET /sites/drafts`
and are confirmed, renamed, merged or rejected through the API. They are never treated as verified
monuments. Missing attribution is stored as `unknown`, never invented.

## API reference

The behavioural contract is [`docs/API.md`](docs/API.md); the quick integration map is
[`docs/api-contracts.md`](docs/api-contracts.md); the generated schema is
[`docs/openapi.json`](docs/openapi.json) (39 paths). FastAPI also serves live OpenAPI at `/docs` and
`/openapi.json`.

| Group | Endpoints | Purpose |
|---|---|---|
| Health | `GET /health`, `GET /readiness` | Database and model status; 503 when the database is unavailable |
| Sites | `GET /sites`, `POST /sites`, `GET /sites/{id}`, `PATCH /sites/{id}` | List with region/category/tag/verified filters, create, detail, update |
| Related | `GET /sites/{id}/related?k=&alpha=` | Explainable CLIP + tag-overlap recommendations |
| Drafts | `GET /sites/drafts`, `POST /sites/{id}/confirm`, `POST /sites/{id}/reject`, `POST /sites/{id}/merge` | Review EXIF-derived location clusters |
| Upload | `POST /images/upload`, `POST /images/upload-batch` | Multipart upload with attribution and site creation; `202` and job id |
| Images and jobs | `GET /images/{id}`, `GET /images/{id}/tags`, `POST /images/{id}/reprocess`, `GET /jobs/{id}` | Image metadata, tags, re-embedding and job status |
| Ingestion | `GET /ingest/batches`, `GET /ingest/batches/{id}` | Folder-ingestion progress and per-file report |
| Search | `GET /search/text`, `GET /search/images`, `POST /search/by-image` | MiniLM site search; CLIP text-to-image and image-to-image |
| Review | `GET /review/queue`, `GET /review/reviewers`, `POST /review/tags/{id}`, `POST /review/tags/add`, `GET /review/history/{id}` | Queue, confirm/reject, human-added tags, append-only history |
| Trails | `POST/GET /trails`, `GET/PATCH /trails/{id}`, `POST /trails/{id}/stops`, `DELETE /trails/{id}/stops/{stop_id}`, `PATCH /trails/{id}/stops/reorder`, `POST /trails/from-images`, `GET /trails/{id}/summary`, `GET /trails/{id}/journal` | Ordered itineraries, distances and journal |
| Users | `POST/GET /users`, `GET /users/{id}` | Minimal reviewer records (no authentication) |
| AI (optional) | `GET /ai/status`, `POST /ai/chat`, `POST /ai/explain/{site_id}`, `POST /ai/trails/suggest` | Grounded assistant, site explanation and thematic trail suggestion |

Errors use `{"detail": "message"}` with 400 (bad input), 404 (missing), 409 (constraint), 413 (upload
too large), 422 (validation), 500 (unexpected) and 503 (database unavailable). All scores in
responses are raw cosine similarities in `[-1, 1]`, never probabilities.

## Dataset and provenance

The committed dataset is small and curated, not scraped broadly.

| Item | Value |
|---|---|
| Sites | 30 (15 Gujarat, 15 Rajasthan) |
| Images | 150 (5 per site), all unique |
| Total image size | 114.3 MB |
| Validation result | 0 errors, 0 warnings |
| Site categories | fort 8, palace 7, temple 6, stepwell 4, mosque 3, haveli 2 |
| Descriptions | 26 from Wikipedia, 4 from Wikidata; source URL stored per site |
| Licences | CC BY 2.0/3.0, CC BY-SA 2.0/2.5/3.0/4.0, CC0, No restrictions, Public domain |
| Per-image metadata | Author, licence name, source URL, original dimensions and local path for all 150; licence URL for 148 of 150 |

Provenance is kept by design:

- Author, licence, licence URL and source URL are stored **per image**, not per site.
- `licence_url` is empty for 2 images in the committed manifest; those records still carry the
  licence name and the Commons source URL. The project does not claim complete licence-URL coverage.
- The download script records the Commons file page, author, licence and dimensions at download time.
  `validate_images.py` rejects rows without the required attribution fields.
- Missing attribution during folder ingestion is stored as `unknown`, never guessed.
- EXIF camera data is preserved in `images.exif`; `captured_at` is set only when EXIF provides it.
- AI never overwrites `sites.description`, `trail_stops.note` or image attribution.

Committed artefacts: `data/dataset/manifest.json`, `sites.json`, `images.json`, `validation.json`,
`REPORT.md` and `data/sites.csv`; the 150 JPEGs live in `data/dataset/images/` under Git LFS.
Downloads go to `data/raw/`, which is gitignored.

Dataset pipeline (from the repository root):

```bash
python -m scripts.dataset.download_wikimedia   # Commons API -> data/raw (skips existing files)
python -m scripts.dataset.generate_metadata    # writes data/sites.csv and JSON manifests
python -m scripts.dataset.validate_images      # dimensions, duplicates, attribution
python -m scripts.dataset.generate_report      # rewrites data/dataset/REPORT.md
```

`download_roboflow` is optional and exits cleanly when its four environment variables are unset.

## Responsible AI and limitations

These are explicit, current limitations. They should be shown to judges and users rather than
hidden.

- **AI tags are suggestions, not historical facts.** They are stored with status `auto` and must be
  reviewed before being treated as verified.
- **No automatic feature tags are emitted today.** All seven per-label thresholds in
  `backend/app/feature_prompts.json` are `null` because no human tuning data exists. The worker
  writes zero feature tags; an empty list is the intended safe behaviour.
- **The Review Queue is currently empty** for the same reason. The UI handles the empty state, and a
  reviewer can only act on existing suggestions.
- **No human-reviewed tags exist in the shipped data.** Verified and human-added tags will appear
  only after a reviewer acts on a populated queue.
- **No independently human-labelled dataset exists**, so model accuracy, precision, recall and F1
  are **not measured** and must not be claimed. There is no precision@5 measurement either.
- **CLIP cosine similarity is not a probability.** It is a raw similarity in `[-1, 1]` and is shown
  as a number. It must not be rendered as a percentage or "confidence".
- **CLIP and MiniLM embeddings are not comparable.** CLIP is 512-d and represents images/text in one
  space; MiniLM is 384-d and represents site descriptions in another. Cross-space cosine scores are
  meaningless.
- **Explorer Trail distances are straight-line Haversine distances**, not road, driving or walking
  routes. The API always returns `distance_mode: "straight_line"`.
- **EXIF coverage is limited.** In a release-preparation dry run over 160 raw files, 2 carried GPS
  and none carried a usable capture timestamp. EXIF-derived trails can therefore contain few or no
  stops.
- **Location input is manual or EXIF-based.** There is no place-name geocoding service in this
  build; coordinates come from EXIF or the map picker and are always correctable.
- **Authentication is not implemented.** There is no login, token or API key. The reviewer list is a
  fixed audit label and can be impersonated. Do not expose write endpoints publicly without adding
  authentication.
- **The assistant is optional and not a verification layer.** It is disabled by default, answers
  only from retrieved rows, returns its sources and `ai_generated` flag, and falls back to
  deterministic text when unavailable. It can still misinterpret records; it never changes them.
- **The dataset is small and mostly English.** Results are exploratory and do not generalise beyond
  the curated corpus.
- **Database-backed behaviour was not exercised in the local verification environment.** No
  PostgreSQL was available, so 45 database tests were skipped; they require `TEST_DATABASE_URL` and
  run in CI against a pgvector service.

Human oversight matters because the archive mixes original records, machine suggestions and human
decisions. Without the review step, a wrong tag becomes indistinguishable from a documented fact.
The schema and UI therefore keep the three layers separate and append every decision to
`tag_reviews`.

## Testing and evaluation

### Automated tests

Backend, from the repository root:

```bash
pytest backend/tests -q
```

Database tests need a PostgreSQL database whose name ends in `_test`:

```bash
TEST_DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas_test pytest backend/tests -q
```

Frontend, from `frontend/`:

```bash
npm test
```

Verified in this working tree:

| Command | Result |
|---|---|
| `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` | **59 passed, 45 skipped** (the 45 require `TEST_DATABASE_URL`) |
| `npm test` (frontend) | **16 passed** in 1 test file |
| `ruff check backend scripts` | **All checks passed** |
| `mypy` | **Success: no issues found in 48 source files** |
| `npm run lint` (frontend) | Passed |
| `npm run build` (frontend) | Passed; 8 routes generated |

The full local check is `make check` (ruff, mypy, pytest). A skipped database test is not a passing
test; see [`docs/SUBMISSION_READINESS.md`](docs/SUBMISSION_READINESS.md) for the executed-versus-skipped
breakdown.

### Model evaluation

Evaluation is script-driven and refuses to invent numbers:

```bash
python backend/scripts/eval_tagging.py --template   # empty annotation sheet
python backend/scripts/tune_tagging.py --write      # per-label thresholds on tuning sites only
python backend/scripts/eval_tagging.py              # baseline vs revised vs negatives
python backend/scripts/eval_fewshot.py              # logistic probe vs zero-shot
python backend/scripts/eval_search.py               # precision@5 + latency
python backend/scripts/eval_review_stats.py         # review counts by tag
```

Current status: no annotation sheet exists, so tagging metrics are `not_measured`; no relevance
judgements exist, so precision@5 is `not_measured`; review statistics are review counts, not
accuracy. An earlier checkpoint recorded single-query timings (text search 101 ms, text-to-image
103 ms, image-to-image 264 ms on 31 Oct 2026, warm models); these are not a benchmark and were not
re-measured here. See [`docs/EVALUATION.md`](docs/EVALUATION.md) for the methodology.

The end-to-end checkpoint script exists for a seeded database:

```bash
python backend/scripts/checkpoint.py
```

It uploads a cropped dataset photo, drains the worker, and exercises text search, text-to-image,
image-to-image, related sites, review and trails. It was not run in this environment because no
PostgreSQL was available.

## Scalability and roadmap

### Current design

- **Stateless API.** Request handlers hold no session state; any number of API processes can run
  behind a load balancer.
- **Database-backed queue.** The worker claims jobs with `FOR UPDATE SKIP LOCKED`, so workers scale
  horizontally without a separate broker. Leases, retries and backoff are persisted.
- **HNSW indexes** on both vector columns provide approximate nearest-neighbour search that grows
  with the archive.
- **Embeddings computed once.** Searches embed only the incoming query; stored embeddings are reused.
- **Explicit provenance and audit tables** make later human-review tooling possible without a schema
  rewrite.

### Proposed work

| Area | Proposal |
|---|---|
| Authentication and roles | Real accounts, role-based access (`admin`, `reviewer`, `researcher`, `visitor`), protect write endpoints |
| More archives | Additional regions, languages and partner collections with the same provenance rules |
| Human-reviewed metadata | Collect annotation sheets, tune per-label thresholds, populate the review queue, measure precision/recall/F1 |
| Search evaluation | Build relevance judgements and a repeatable precision@5 benchmark |
| Scalable processing | Move the queue to Redis/Celery or a managed queue; batch embedding on GPU; object storage plus CDN for images |
| Production hosting | Managed PostgreSQL with pgvector, container deployment, observability, backups and rate limiting |
| Model reproducibility | Store model and prompt versions per run (for example a `model_runs` table) |

These are proposals, not implemented features. They are listed to separate the working build from
future work.

## Repository structure

```
heritage-atlas/
├── backend/
│   ├── app/
│   │   ├── routers/            sites, images, jobs, search, review, ingestion, trails, users, ai
│   │   ├── repositories/       parameterised SQL per entity
│   │   ├── services/           AI grounding, ranking, geo, trails, journal, ingestion, licences
│   │   ├── main.py             FastAPI app, static /files mount, health and readiness
│   │   ├── ml.py               CLIP and MiniLM embeddings, zero-shot tagging
│   │   ├── ai.py               Gemini provider with rate limit and retries
│   │   ├── config.py           environment-backed settings
│   │   ├── db.py               Psycopg connection helpers
│   │   ├── schemas.py          Pydantic request/response models
│   │   └── feature_prompts.json
│   ├── scripts/                init_db, load_dataset, embed_descriptions, ingest_folder,
│   │                           checkpoint, smoke_test, evaluation scripts
│   ├── tests/                  pytest unit and API tests
│   ├── worker.py               database-backed job worker
│   └── requirements*.txt
├── db/
│   ├── schema.sql              source of truth
│   └── migrations/             001_backend_expansion.sql, 002_phase1.sql
├── scripts/dataset/            Wikimedia/Roboflow download, metadata, validation, report
├── data/
│   ├── dataset/                manifest.json, sites.json, images.json, validation.json,
│   │                           REPORT.md, images/ (150 JPEGs, Git LFS)
│   └── sites.csv
├── frontend/
│   ├── app/                    /, /search, /upload, /review, /trails, /sites/[id]
│   ├── components/             map, gallery, provenance chips, cinematic home, trails
│   ├── lib/                    api.ts (all API calls), types.ts, mocks/
│   └── package.json
├── docs/                       PRD, architecture, API, dataset, evaluation, reports
├── uploads/                    local image storage served at /files (gitignored contents)
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── .env.example
└── README.md
```

## Documentation

| Document | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Problem, users, scope, acceptance criteria, risks |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, embedding spaces, flows, scalability, limitations |
| [`docs/API.md`](docs/API.md) | API behaviour and response shapes (source of truth) |
| [`docs/api-contracts.md`](docs/api-contracts.md) | Quick endpoint map for integration |
| [`docs/openapi.json`](docs/openapi.json) | Generated OpenAPI schema |
| [`docs/DATASET.md`](docs/DATASET.md) | Data sourcing, licensing rules and dataset pipeline |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | How tagging and search are evaluated |
| [`docs/SUBMISSION_READINESS.md`](docs/SUBMISSION_READINESS.md) | Verified, skipped and blocked work; security findings |
| [`docs/FRONTEND_HANDOFF.md`](docs/FRONTEND_HANDOFF.md) | Frontend integration rules for trails, provenance and errors |
| [`docs/PHASE_1_ENGINEERING_REPORT.md`](docs/PHASE_1_ENGINEERING_REPORT.md) | Tagging, retrieval, ingestion, review and reliability fixes |
| [`docs/FINAL_ENGINEERING_REPORT.md`](docs/FINAL_ENGINEERING_REPORT.md) | Historical build snapshot (superseded) |
| [`docs/TASKS.md`](docs/TASKS.md) | Task board by lane |
| [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Branch, review and commit rules |
| [`db/schema.sql`](db/schema.sql) | Database schema (source of truth) |
| [`DESIGN.md`](DESIGN.md) | UI design system and provenance rules |
| [`AGENTS.md`](AGENTS.md) | Rules for AI coding agents |
| [`frontend/README.md`](frontend/README.md) | Frontend package notes |

## Design rules

These rules are enforced across the codebase and should guide future changes:

1. CLIP (512-d) and MiniLM (384-d) are separate embedding spaces; never compare across them.
2. Tag scores are raw cosine similarities, never probabilities or confidence percentages.
3. AI output never overwrites original notes. Tag status is `auto | verified | rejected | added_by_human`
   and reviews are append-only in `tag_reviews`.
4. Licence and author are stored per image.
5. Heavy ML runs in the worker; only a single query embedding runs inside a request.
6. Schema and API contract changes land in the same change as the code that depends on them.
7. The UI always shows the provenance layer (original, suggested, verified) per [`DESIGN.md`](DESIGN.md).
