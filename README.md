# Heritage Atlas

From fragmented heritage records to verified, explorable cultural journeys. HackCult '26, track HC26-CULT01.

## Documentation
| File | Purpose |
|---|---|
| docs/PRD.md | Problem, users, scope, acceptance criteria, risks |
| docs/ARCHITECTURE.md | Components, embedding spaces, flows, scalability, limitations |
| docs/API.md | API contract |
| db/schema.sql | Database schema |
| DESIGN.md | UI design system |
| docs/DATASET.md | Data sourcing and licence rules |
| docs/EVALUATION.md | How results are measured |
| docs/TASKS.md | Task board by lane |
| docs/WORKFLOW.md | Working with multiple agents |
| AGENTS.md | Rules for AI coding agents |

## Backend setup

### Prerequisites
PostgreSQL 15+ with the `pgvector` extension, reachable via `DATABASE_URL`. Pick one:
- Hosted (easiest, no install): a free Neon or Supabase project. pgvector is built in.
- Local install: PostgreSQL + pgvector from your OS package manager.

### Run
    cp .env.example .env                 # set DATABASE_URL
    cd backend && python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    python scripts/init_db.py            # applies db/schema.sql
    uvicorn app.main:app --reload        # terminal 1
    python worker.py                     # terminal 2 (first run downloads CLIP + MiniLM)

## Day 2 acceptance test: upload -> tag -> embed -> search
    curl -F file=@photo.jpg -F site_name="Rani ki Vav" -F region=Gujarat -F lat=23.8593 -F lon=72.1018 \
         -F description="Stepwell with carved pillars" -F author="..." -F licence="CC BY-SA 4.0" \
         http://localhost:8000/images/upload
    curl http://localhost:8000/jobs/1                       # wait for "done"
    curl "http://localhost:8000/search/images?q=carved+stone+pillars"
    curl http://localhost:8000/review/queue

## Design rules
- CLIP (512-d) and MiniLM (384-d) are separate spaces; never compare across them.
- Tag scores are raw cosine similarities, not probabilities. Tune FEATURE_THRESHOLD in app/ml.py.
- AI never overwrites original notes; every review is appended to tag_reviews.
