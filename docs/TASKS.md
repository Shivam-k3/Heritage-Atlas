# Task board (update as you go)

Lanes: **B** backend/ML (opencode), **F** frontend (Antigravity), **Q** tests/docs/review (Copilot + human).
Dates: D1 Sat 31 Oct, D2 Sun 1 Nov, D3 Mon 2 Nov, D4 Tue 3 Nov, D5 Wed 4 Nov (submit by 4:00 PM, deadline 6:30 PM IST).

## D1 Foundation
- [x] B: run scaffold, pass the upload -> tag -> embed -> search test (smoke_test.py)
- [ ] F: Next.js + TypeScript + Tailwind skeleton, Leaflet map reading /sites
- [x] Q: collect 20-30 sites with licences in data/sites.csv; commit docs
## D2 Pipeline and pages
- [x] B: seed loader, EXIF GPS, filters on /sites and search
- [ ] F: site page, upload page, search page (text and image)
- [x] Q: tests for upload validation and tagging
- [x] Checkpoint: upload a real photo, get tags, retrieve it by text query
## D3 Verification and related sites
- [x] B: split main.py into routers, related sites, review history
- [ ] F: review queue UI, provenance labels, related sites panel
- [x] Q: API tests, review the diffs against AGENTS.md
## D4 Trails and polish
- [x] B: trails endpoints, haversine, journal generator (with tests)
- [ ] F: trail builder, route on map, journal view, loading/error/empty states
- [ ] Q: label evaluation photos; bug bash on the full flow
## D5 Evidence and submission
- [x] B: eval scripts and numbers (scripts done; labels not collected, metrics not measured)
- [ ] F: UI polish, mobile pass
- [ ] Q: README with architecture diagram, 10-slide deck, 2-3 min video, final CI green
- [ ] Submit repo, video link, deck PDF link

## D4/D5 Final backend sprint (3 Nov)
- [x] B: EXIF GPS error handling, blank search/label validation, DB integrity -> 409
- [x] B: bounded image-search upload read
- [x] B: Trails update, remove-stop renumbering, ordered coordinates, straight-line mode,
      missing-coordinate reporting
- [x] B: EXIF-derived trail generation (`POST /trails/from-images`)
- [x] B: unit tests for the new branches; API tests written for DB execution
- [x] B: regenerate `docs/openapi.json`, update `docs/API.md`, `docs/api-contracts.md`, README
- [ ] B: run the 45 database tests and full ingestion against Supabase (blocked: no credentials)
- [ ] B: collect human labels, tune thresholds, run ML evaluation (blocked: no annotations)

## Cut order if late
Public sharing, story mode, OSRM routing, advanced related-site explanations. Never cut: upload pipeline, map, search, verification.
