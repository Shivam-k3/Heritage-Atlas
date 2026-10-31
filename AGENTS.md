# Project rules for AI coding agents (opencode, Antigravity, Copilot)

Heritage Atlas: FastAPI + PostgreSQL/pgvector + CLIP/MiniLM backend, Next.js + Leaflet frontend.
Judged on: technical execution and code quality (40%), architecture and scalability (30%), UI/UX (20%), innovation (10%).

## Read first, in this order
1. `docs/PRD.md` what we build and the scope limits
2. `docs/ARCHITECTURE.md` how it works
3. `docs/API.md` and `db/schema.sql` the contracts (source of truth)
4. `DESIGN.md` for any UI work
5. `docs/WORKFLOW.md` for lanes, branches, review rules
6. Your lane file: `backend/AGENTS.md` or `frontend/AGENTS.md`
Then pick a task from `docs/TASKS.md`. If a request conflicts with these files, say so instead of guessing.

## Non-negotiable design rules
1. CLIP (512-d) and MiniLM (384-d) are separate embedding spaces. Never compare across them.
2. Tag scores are raw cosine similarities. Never call them probabilities or confidence percentages.
3. AI output never overwrites original notes. Tag status: auto | verified | rejected | added_by_human. Reviews are append-only (tag_reviews).
4. Licence and author are stored per image.
5. Heavy ML work runs in the worker, not in a request handler (embedding one search query or one search photo is the exception).
6. Schema and API contract change first, in the same PR as the code.
7. The UI always shows the provenance layer (original, suggested, verified) per `DESIGN.md`.

## Code standards
- Python 3.11+, type hints on every function signature, small functions, no dead or commented-out code.
- Lint and format with ruff. No unused imports, no bare `except:`.
- SQL is always parameterised. Never build SQL with f-strings.
- Route handlers stay thin; model code in `ml.py`; DB access in `db.py`.
- Frontend: TypeScript strict, no `any`, API calls only through `frontend/lib/api.ts`, loading/error/empty state on every fetch.
- No hardcoded demo data in the UI. No secrets in git; use environment variables and keep `.env.example` current.

## Workflow
- Feature branch per task, small commits: `feat|fix|docs|test|refactor|chore(scope): message`.
- Before finishing run `make check` (or `ruff check`, `ruff format --check`, `pytest` directly). Do not disable rules or delete tests to pass.
- New behaviour needs a test; a bug fix needs a regression test.
- Do not add dependencies without a reason in the commit message.
- Do not invent metrics. Evaluation numbers come only from `backend/scripts/eval_*.py`.
- At the end of every task print a report: what changed, commands run with results, bugs found, anything unresolved.
