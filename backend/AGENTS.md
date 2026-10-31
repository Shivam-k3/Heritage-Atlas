# Backend lane rules (opencode)
Scope: `backend/`, `db/`, `scripts`. Do not edit `frontend/`.
- Follow `/AGENTS.md`. Implement endpoints exactly as in `docs/API.md`; update that file when behaviour changes.
- Split `app/main.py` into `app/routers/{sites,search,review,trails,upload}.py` once trails are added.
- Put pure logic (haversine, journal generation, Jaccard, score fusion) in plain functions in `app/services/` so they are unit-testable without a database or models.
- Keep `sentence_transformers` imports lazy so tests and CI stay fast.
- Worker must be idempotent: re-running a job must not duplicate tags.
- Tests: pytest. Pure functions get unit tests; endpoints get tests against a test database.
