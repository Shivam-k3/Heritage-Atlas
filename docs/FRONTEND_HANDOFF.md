# Frontend API handoff

Date: 3 November 2026. Backend contract: `docs/API.md`, `docs/openapi.json` (34 paths) and
`docs/api-contracts.md`. This page covers the parts the frontend must not guess: Trails, related
sites, review/provenance, errors and empty states.

Base URL comes from `NEXT_PUBLIC_API_URL`. Every call goes through `frontend/lib/api.ts`. The
functions listed below already exist in the local frontend working tree and call the real API; keep
them and verify them against this contract. Do not add mock fallbacks for these endpoints.

## 1. Trails

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/trails` | `TrailCreate` | `TrailOut` (201) |
| GET | `/trails` | `created_by`, `is_public`, `limit`, `offset` | `TrailOut[]` |
| GET | `/trails/{id}` | - | `TrailOut` |
| PATCH | `/trails/{id}` | partial `TrailUpdate` | `TrailOut` |
| POST | `/trails/{id}/stops` | `TrailStopCreate` | `TrailStopOut` (201) |
| DELETE | `/trails/{id}/stops/{stop_id}` | - | `TrailStopOut[]` |
| PATCH | `/trails/{id}/stops/reorder` | `{"stop_ids": [int, ...]}` | `TrailStopOut[]` |
| POST | `/trails/from-images` | `TrailFromImages` | `TrailFromImagesOut` (201) |
| GET | `/trails/{id}/summary` | - | `TrailSummaryOut` |
| GET | `/trails/{id}/journal` | - | `JournalOut` |

### Shapes

```ts
interface TrailStopOut {
  id: number;
  site_id: number;
  site_name: string;
  region: string | null;
  category: string | null;
  lat: number | null;
  lon: number | null;
  stop_order: number;          // 1-based, contiguous after every mutation
  visit_date: string | null;   // "YYYY-MM-DD"
  note: string | null;
}

interface TrailOut {
  id: number;
  title: string;
  description: string | null;
  created_by: string | null;
  is_public: boolean;
  created_at: string;          // ISO 8601
  stops: TrailStopOut[];
}

interface TrailFromImagesOut {
  trail: TrailOut;
  images_used: number;         // images with both a capture time and site coordinates
  images_skipped: number;      // everything else, never guessed
}

interface TrailSummaryOut {
  trail_id: number;
  title: string;
  sites: number;
  photos: number;
  total_km: number;
  distance_mode: "straight_line";
  missing_coordinates: number[]; // site ids that could not be measured
  top_features: string[];
  legs: { from: number; to: number; km: number }[]; // site ids, in stop order
}

interface JournalOut {
  trail_id: number;
  title: string;
  generated: true;
  entries: {
    stop_order: number;
    site_id: number;
    site_name: string;
    visit_date: string | null;
    original_note: string | null;   // user text, never overwritten
    generated_summary: string;      // template text, always labelled as generated
    generated: true;
    photos: number;
    verified_features: string[];
  }[];
}
```

### Request rules

- `TrailCreate`: `title` required, non-blank, max 200; `description` max 20 000; `is_public`
  defaults to `false`.
- `TrailUpdate`: send at least one of `title`, `description`, `is_public`. Unknown fields and an
  empty body return 422. A blank title returns 422.
- `TrailStopCreate`: `site_id` required; optional `visit_date` (`YYYY-MM-DD`) and `note`.
  A missing trail or site returns 404.
- `PATCH /trails/{id}/stops/reorder`: `stop_ids` must be an exact permutation of the trail's current
  stop ids. Anything else returns 400. The response is the full reordered list.
- `DELETE /trails/{id}/stops/{stop_id}` returns the remaining stops, renumbered from 1.
- `POST /trails/from-images`: optional `image_ids`; when omitted it scans all images. If no image has
  both a capture time and site coordinates it returns **400**, not an empty trail. Show
  `images_used` / `images_skipped` after success.
- A trail with no stops is valid: `sites: 0`, `photos: 0`, `total_km: 0`, `legs: []`.

### UI rules

- Distances are **straight-line Haversine only**. Label them "straight-line" or "as the crow flies".
  Never call them road, driving or route distance.
- Draw the map polyline only between consecutive stops that both have `lat`/`lon`. Do not invent a
  line across a stop in `missing_coordinates`; show "distance unavailable for N stops" instead.
- After add/remove/reorder, use the returned ordered list (or refetch the trail). Do not renumber
  stops locally.
- Journal: show `original_note` and `generated_summary` in separate labelled blocks ("Your note" vs
  "Generated summary"). Never merge or overwrite the original note.
- Trail list: loading, error and empty states. An empty list means no trails, not a failure.
- Do not offer a mock "from photos" trail. If the photo set lacks EXIF, explain that the backend
  skips images without a capture time and coordinates.

## 2. Related sites

`GET /sites/{id}/related?k=6&alpha=0.6` returns:

```ts
interface RelatedSiteOut {
  site_id: number;
  name: string;
  score: number;          // raw cosine similarity
  clip_similarity: number;
  tag_overlap: number;    // Jaccard overlap
  shared_tags: string[];
  evidence: Record<string, number | null>; // image counts / tag counts behind the score
}
```

Show the evidence and `shared_tags`, not only the score. Never render `score` as a percentage or
confidence. A site with no images or tags may legitimately return an empty array.

## 3. Review and provenance

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/review/queue` | `limit`, `offset`, `status` | `ReviewQueueOut[]` |
| GET | `/review/reviewers` | - | `string[]` |
| POST | `/review/tags/{image_tag_id}` | `{"action": "confirm" \| "reject", "reviewer": string}` | `ReviewResult` |
| POST | `/review/tags/add` | `{"image_id", "label", "reviewer", "tag_type"?}` | `ReviewResult` |
| GET | `/review/history/{image_tag_id}` | - | `ReviewHistoryOut[]` |

- Tag `status` is `auto | verified | rejected | added_by_human`. Always render it.
- `score` is a raw cosine similarity and may be `null` (human-added tags). Never a percentage.
- Show `model_name`, `model_version` and `prompt_version` when present.
- Rejected tags must not appear as active tags or in search results.
- Review history is append-only. Render it as an audit trail; never edit or delete entries.
- Reviewer values are a fixed demo list, not authentication. Do not present them as logged-in users.
- The queue can be empty because all thresholds are `null` and the model intentionally emits no auto
  tags. Show "No tags awaiting review" rather than an error.

## 4. Errors and empty states

- Errors use FastAPI's shape: `{"detail": "..."}`. Validation errors use `{"detail": [...]}`.
  Show the `detail` text; do not render stack traces or internal paths.
- `503` means the database is unavailable. Show a retry state.
- `404` means the trail, site, stop or tag does not exist; show a not-found state.
- `400` on reorder means the ids are not a permutation. `400` on `from-images` means no usable EXIF.
- `422` means a request validation failure; surface the field message.
- Every fetch needs loading, error and empty states. Do not substitute hardcoded demo data.

## 5. Attribution and scores

- Images carry `author`, `licence`, `licence_url` and `source_url` per image. Show them with the image;
  do not fall back to a site-level credit.
- Use `/files/...` URLs exactly as returned. Never build filesystem paths.
- Scores are raw cosine similarities. No percentages, no confidence wording, no invented thresholds.

## 6. Acceptance checklist

- [ ] Trail create, add stops, reorder, remove, summary and journal work against the real API.
- [ ] `distance_mode` is shown as straight-line; `missing_coordinates` is surfaced.
- [ ] `original_note` and `generated_summary` are visually separate.
- [ ] `from-images` shows `images_used` / `images_skipped` and handles 400 honestly.
- [ ] Related sites show evidence and `shared_tags`.
- [ ] Review queue shows status and model provenance; history is append-only.
- [ ] No score is rendered as a percentage or confidence.
- [ ] Loading, error and empty states exist for every fetch.
- [ ] `npm run lint`, `npm run build` and the frontend tests pass.
