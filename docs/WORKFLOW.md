# Working with multiple agents

| Lane | Tool | Owns | Does not touch |
|---|---|---|---|
| Backend and ML | opencode | backend/, db/, scripts | frontend/ |
| Frontend | Antigravity | frontend/ | backend/ |
| Tests, docs, review | Copilot + human | backend/tests, docs/ | feature code |

## Rules
1. One tool per task, one task per prompt, each ending with a written report.
2. Use a git worktree or separate clone per lane. Never two agents in one folder.
3. Branch `feat/<area>-<task>`; PR into `main`; CI green; a human reads the diff before merge.
4. Reviewer is a different tool from the author.
5. Contracts first: `db/schema.sql` and `docs/API.md` change before the code that depends on them.
6. Only one lane edits `requirements.txt`; only one edits `package.json`.
7. Commits: `feat|fix|docs|test|refactor|chore(scope): message`, small and frequent, inside the hackathon window.
8. Before merge: `make check` passes. Never disable lint rules or delete tests to pass.
9. Rebase on `main` at the start of each session.
