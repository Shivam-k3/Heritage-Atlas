# Product Requirements: Heritage Atlas

Track HC26-CULT01 (Culture & Digital Heritage), HackCult '26. Submission deadline: 4 Nov 2026, 6:30 PM IST.

## 1. Problem
Field documentation of heritage sites (photos, notes, locations) ends up scattered across slide decks,
cloud folders and text reports. Researchers, tourists and archivists cannot search it, see it on a map,
find similar structures, or tell which information was checked by a person.

## 2. Vision
Turn fragmented heritage field documentation into a verified, searchable, explorable archive:
**from fragmented records to verified, explorable cultural journeys.**

## 3. Users
| User | Need |
|---|---|
| Field researcher / Explorer Fellow | Upload photos and notes quickly; get structure without manual labelling; assemble a trip into a journal |
| Heritage reviewer / archivist | Confirm or correct AI suggestions; keep a record of who decided what |
| Visitor (researcher, tourist) | Find sites by description or by photo; see them on a map; follow a trail |

## 4. Principles
1. Three layers of information are always visually distinct: **original source**, **AI-suggested**, **human-verified**.
2. AI never overwrites original notes or attribution.
3. Scores are raw similarities, never presented as probabilities.
4. A small, well-curated dataset that works end to end beats a broad one that does not.

## 5. Scope
### Must have (MVP)
| ID | Requirement | Acceptance criteria |
|---|---|---|
| F1 | Interactive map | Sites appear as pins from the database; clicking opens a preview; filter by region, type, tag, verified-only |
| F2 | Site page | Gallery, original notes, tags with provenance labels, per-image author and licence, related sites |
| F3 | Upload pipeline | Photo + notes + location + attribution accepted; job runs asynchronously; failure never deletes the upload |
| F4 | Auto-tagging | CLIP zero-shot assigns one site type and up to 4 features from a fixed vocabulary; raw score stored |
| F5 | Text search | Sentence-Transformers over site descriptions; returns ranked sites |
| F6 | Text-to-image search | CLIP text encoder against image embeddings; returns ranked photos |
| F7 | Image-to-image search | Upload a photo, get visually similar photos from other sites |
| F8 | Human verification | Queue sorted by lowest score; confirm, reject, add tag; append-only audit log |
| F9 | Explorer Trails | Ordered stops, route on the map, haversine distances, generated timeline journal that keeps original notes visible |
### High priority
| ID | Requirement |
|---|---|
| F10 | Explainable related sites (CLIP similarity + tag overlap, with shared tags and photos shown) |
| F11 | Location input: EXIF GPS, map pin, place-name geocoding, always manually correctable |
### Bonus (cut in this order if late)
Public trail sharing, story mode, OSRM road routing, advanced related-site explanations.
### Out of scope
OCR, 3D reconstruction, knowledge graph, custom model training, claim extraction and conflict detection (roadmap slide only).

## 6. Non-functional requirements
- Search responds in under 1.5 s on the demo dataset (excluding first model load).
- Upload returns immediately; processing is asynchronous.
- No secrets in the repo; configuration via environment variables.
- Responsive down to a 375 px wide phone; keyboard-accessible; sufficient contrast.
- Licence and author are stored for every image.

## 7. Success metrics (measured, reported honestly)
- Tagging precision/recall/F1 per tag on 30-50 hand-labelled photos.
- Precision@5 on 10-15 text-to-image and image-to-image queries.
- End-to-end demo runs without hardcoded data.
Targets are reported, not promised. See `docs/EVALUATION.md`.

## 8. Judging alignment
| Criterion | Weight | How this project addresses it |
|---|---|---|
| Technical execution and code quality | 40% | Working pipeline, tests, lint, CI, small commits, no hardcoded demo data |
| Architecture and scalability | 30% | Async worker queue, pgvector HNSW, separated embedding spaces, stateless API, documented schema |
| UI/UX | 20% | Map-first interface, provenance labels, designed per `DESIGN.md` |
| Innovation and problem fit | 10% | Verification layer and Explorer Trails built on the Explorer Fellowship use case |

## 9. Risks
| Risk | Mitigation |
|---|---|
| CLIP mislabels features | Verification queue, threshold tuned on labelled set, failures documented |
| Dataset too thin | Themed set (Gujarat + Rajasthan), 20-30 sites, 3-8 photos each, collected on Day 1 |
| Integration across three people | Contracts in `docs/API.md` and `db/schema.sql`; daily end-to-end run |
| Scope creep | Cut order in section 5; features outside it are rejected |

## 10. Roadmap (final slide)
OCR for regional documents, multilingual search, claim extraction with source-conflict detection,
fine-tuning CLIP on verified heritage data, condition and conservation tagging, 3D reconstruction.
