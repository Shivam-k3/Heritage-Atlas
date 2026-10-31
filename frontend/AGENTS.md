# Frontend lane rules (Antigravity)
Scope: `frontend/`. Do not edit `backend/`.
- Follow `/AGENTS.md` and `/DESIGN.md` exactly. Design tokens live in the Tailwind theme; no raw hex in components.
- Stack: Next.js (App Router), TypeScript strict, Tailwind, Leaflet + OpenStreetMap, marker clustering.
- API base URL from `NEXT_PUBLIC_API_URL`. Types mirror `docs/API.md`; all calls go through `lib/api.ts`.
- Until an endpoint exists, use a typed mock inside `lib/mocks/` selected by an env flag, never inline in components.
- Every fetch has loading, error and empty states. Test keyboard navigation and a 375 px viewport.
- Run `npm run lint` and `npm run build` before finishing a task.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
