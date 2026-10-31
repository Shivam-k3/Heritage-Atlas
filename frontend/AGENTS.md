# Frontend lane rules (Antigravity)
Scope: `frontend/`. Do not edit `backend/`.
- Follow `/AGENTS.md` and `/DESIGN.md` exactly. Design tokens live in the Tailwind theme; no raw hex in components.
- Stack: Next.js (App Router), TypeScript strict, Tailwind, Leaflet + OpenStreetMap, marker clustering.
- API base URL from `NEXT_PUBLIC_API_URL`. Types mirror `docs/API.md`; all calls go through `lib/api.ts`.
- Until an endpoint exists, use a typed mock inside `lib/mocks/` selected by an env flag, never inline in components.
- Every fetch has loading, error and empty states. Test keyboard navigation and a 375 px viewport.
- Run `npm run lint` and `npm run build` before finishing a task.
