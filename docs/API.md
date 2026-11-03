# API contract

Base URL (dev): `http://localhost:8000`. JSON unless noted. Tag and search scores are raw cosine
similarities in [-1, 1]; they are never probabilities. The generated machine contract is
`docs/openapi.json` (34 paths). Change this file in the same PR as any API change.

## Sites
### GET /sites
Query: `region`, `category`, `tag` (label), `verified_only` (bool), `limit` (1-1000, default 200),
`offset`. Returns a bare array, not a pagination envelope.
```json
[{"id":1,"name":"Rani ki Vav","region":"Gujarat","district":"Patan","category":"stepwell",
  "lat":23.8593,"lon":72.1018}]
```
### POST /sites -> 201
Body: `name`, optional `region`, `district`, `category`, `lat`, `lon`, `description`,
`description_source`. Returns the site detail.
### GET /sites/{id}
```json
{"id":1,"name":"Rani ki Vav","region":"Gujarat","category":"stepwell","lat":23.8593,"lon":72.1018,
 "description":"original note","description_source":"wikipedia",
 "images":[{"id":4,"site_id":1,"url":"/files/ab/abc.jpg","author":"...","licence":"CC BY-SA 4.0",
   "licence_url":"...","source_url":"...","width":1920,"height":1080,"status":"processed",
   "tags":[{"id":9,"label":"carved pillars","tag_type":"feature","score":0.27,"status":"auto"}]}]}
```
### PATCH /sites/{id}
Any subset of the create fields; at least one field is required. Returns the site detail.
### GET /sites/{id}/related?k=5&alpha=0.6
`alpha` overrides the CLIP weight (`RELATED_CLIP_WEIGHT`). `k` is 1-20.
```json
[{"site_id":2,"name":"Adalaj Stepwell","score":0.74,"clip_similarity":0.81,"tag_overlap":0.60,
  "shared_tags":["stepwell","carved pillars"],"evidence":{"image_a":4,"image_b":11}}]
```
### Draft location clusters (folder ingestion)
`GET /sites/drafts?limit=200&offset=0` returns unverified clusters with `status`, `source`,
`images` (count) and `image_ids`. A reviewer can rename a draft with `PATCH /sites/{id}` and then:
- `POST /sites/{id}/confirm` -> promote to `canonical`.
- `POST /sites/{id}/reject` -> keep the photos for audit, mark `rejected`.
- `POST /sites/{id}/merge` with `{"target_site_id": 12}` -> move photos into a canonical site.
Only `status='draft'` sites accept these actions. Draft clusters are never treated as verified
monuments.

## Upload and images
### POST /images/upload -> 202 multipart/form-data
Fields: `file`, and either `site_id` or `site_name`; optional `region`, `district`, `category`,
`site_type`, `lat`, `lon`, `description`, `author`, `licence`, `licence_url`, `source_url`.
```json
{"site_id":1,"image_id":4,"job_id":7,"status":"queued","duplicate":false,"url":"/files/ab/abc.jpg"}
```
Duplicate content (same SHA-256) returns the existing image with `duplicate: true` and no new job
unless the existing image is still queued, processing, or failed.
### POST /images/upload-batch -> 202 multipart/form-data
Same fields as `/images/upload`; repeat `files` for several images. Per-file failures are reported
without aborting the batch:
```json
{"results":[{"site_id":1,"image_id":4,"job_id":7,"status":"queued","duplicate":false,
             "url":"/files/ab/abc.jpg"}],
 "errors":[{"filename":"broken.jpg","error":"file is not a valid JPEG, PNG or WebP image"}],
 "accepted":1,"duplicates":0,"rejected":1}
```
### GET /images/{id}
Full image metadata plus `tags` (label, type, raw score, status).
### GET /images/{id}/tags
Bare array of tags.
### POST /images/{id}/reprocess -> 202
Queues a new job. The worker replaces only auto tags, so human decisions and notes survive.
### GET /jobs/{id}
```json
{"id":7,"image_id":4,"job_type":"process_image","status":"pending|running|done|failed",
 "error":null,"retry_count":0,"created_at":"...","updated_at":"..."}
```
A running job older than `JOB_LEASE_SECONDS` (default 300) is returned to the queue and counts as
an attempt; at `JOB_MAX_RETRIES` it becomes `failed`. Failed retries wait
`JOB_RETRY_BACKOFF_SECONDS * 2^(n-1)` before they are claimable again.

## Folder ingestion
Local folder ingestion is CLI-only because a browser cannot address an arbitrary server path:
`python backend/scripts/ingest_folder.py <folder> [--radius-m 300] [--author ...] [--licence ...]
[--dry-run]`. Browser uploads use `/images/upload-batch`.
- `GET /ingest/batches?limit=50&offset=0` and `GET /ingest/batches/{id}` return batch progress and
  the machine-readable report (per-file status, GPS flag, duplicate id, error).
- The batch report marks missing attribution as `"unknown"`; it never invents a licence.
- Draft clusters created by ingestion are listed by `GET /sites/drafts`.

## Search
All three endpoints accept `region`, `category`, `tag`, `verified_only`, `site_id`, `k` (1-100),
`offset`.
### GET /search/text?q=&k=10
MiniLM over site descriptions. `q` is 1-500 characters and must contain non-whitespace text;
a blank query returns 400.
```json
[{"id":1,"name":"Rani ki Vav","region":"Gujarat","category":"stepwell",
  "description":"...","score":0.61}]
```
### GET /search/images?q=&k=10
CLIP text-to-image.
### POST /search/by-image multipart `file`, `k`
CLIP image-to-image. The uploaded photo's stored SHA-256 match is always excluded, so an indexed
photo cannot return itself. `cross_site=true` also excludes every image from the query image's
site; with no site association only the exact content match is excluded. `exclude_image_id` can
name the stored image explicitly, and `max_per_site` caps how many hits one other site may take on
the returned page. The default response semantics are unchanged.

Both image endpoints return active tags (rejected tags are omitted) with provenance and per-image
attribution:
```json
[{"image_id":4,"site_id":1,"name":"Rani ki Vav","region":"Gujarat","category":"stepwell",
  "url":"/files/ab/abc.jpg","score":0.83,
  "author":"A. Photographer","licence":"CC BY-SA 4.0","licence_url":"https://...",
  "source_url":"https://commons.wikimedia.org/...",
  "tags":[{"id":9,"label":"jali work","tag_type":"feature","score":0.31,"status":"verified",
           "model_name":"clip-ViT-B-32","model_version":"clip-ViT-B-32",
           "prompt_version":"heritage-v2"}]}]
```
`name` is the site name (kept for the existing frontend). `url` is always a `/files/...` public URL,
never a local filesystem path.

## Review
### GET /review/queue?limit=50&offset=0&status=auto
Lowest raw score first. `status` is one of `auto | verified | rejected | added_by_human`.
```json
[{"id":9,"image_id":4,"site_id":1,"site_name":"Rani ki Vav","label":"jali work",
  "tag_type":"feature","score":0.23,"status":"auto","created_at":"...",
  "url":"/files/ab/abc.jpg","author":"A. Photographer","licence":"CC BY-SA 4.0",
  "licence_url":"...","source_url":"...",
  "model_name":"clip-ViT-B-32","model_version":"clip-ViT-B-32","prompt_version":"heritage-v2"}]
```
`url` is a browser-loadable `/files/...` path, never a local filesystem path.
### GET /review/reviewers
Returns the fixed demo reviewer identifiers from `REVIEWERS` (default `asha,ravi,guest`).
### POST /review/tags/{image_tag_id}
Body: `{"action":"confirm|reject","reviewer":"asha","reviewer_id":null}`. `reviewer` must be one of
the configured identifiers. Appends a `tag_reviews` row and returns
`{"id":9,"status":"verified|rejected","previous_status":"auto","new_status":"..."}`.
### POST /review/tags/add
Body: `{"image_id":4,"label":"domes","tag_type":"feature","reviewer":"asha","reviewer_id":null}`.
Creates or promotes an `added_by_human` tag with a null score, and appends a review row.
### GET /review/history/{image_tag_id}
Append-only audit rows, oldest first. The reviewer list is a demo audit label, not authentication;
reviewer identity can be impersonated until real auth is added.

## Trails
Distances are straight-line Haversine great-circle distances, never road or driving distances.
Every summary states this explicitly with `distance_mode: "straight_line"`.
### POST /trails -> 201
Body: `{"title","description","created_by","is_public"}`. `title` must contain non-whitespace text.
### GET /trails?created_by=&is_public=&limit=50&offset=0
### GET /trails/{id}
Trail with ordered `stops` (`id`, `site_id`, `site_name`, `region`, `category`, `lat`, `lon`,
`stop_order`, `visit_date`, `note`).
### PATCH /trails/{id}
Any subset of `title`, `description`, `is_public`; at least one field is required.
### POST /trails/{id}/stops -> 201
Body: `{"site_id","visit_date","note"}`. Appends the next stop order.
### DELETE /trails/{id}/stops/{stop_id}
Removes the stop and renumbers the remaining stops from 1. Returns the ordered remaining stops.
### PATCH /trails/{id}/stops/reorder
Body: `{"stop_ids":[3,1,2]}`. Must contain exactly the trail's stop ids.
### POST /trails/from-images -> 201
Builds a trail from stored photographs. Body:
`{"title","description","created_by","is_public","image_ids":null}`. `image_ids` is optional; when
given, only those images are considered. Images are grouped into one stop per site and ordered by
the earliest `captured_at`. An image is usable only when it has a capture time and its site has
coordinates; the rest are counted, never guessed. Returns:
```json
{"trail":{"id":1,"title":"...","stops":[{"site_id":1,"visit_date":"2026-11-01","stop_order":1}]},
 "images_used":2,"images_skipped":1}
```
A request with no usable image returns 400. Generated trails are ordinary trails: the reviewer can
rename, reorder, add or remove stops afterwards.
### GET /trails/{id}/summary
```json
{"trail_id":1,"title":"...","sites":3,"photos":14,"total_km":212.4,
 "distance_mode":"straight_line","missing_coordinates":[9],
 "top_features":["carved pillars"],"legs":[{"from":1,"to":2,"km":62.1}]}
```
`missing_coordinates` lists unique site ids without coordinates. Legs are omitted for any pair
where either end lacks coordinates, and `total_km` sums only the returned legs.
### GET /trails/{id}/journal
Each entry keeps `original_note` and `generated_summary` as separate fields; generation never
overwrites the note. Generated text is template-based and marked `"generated": true`.

## Users
`POST /users`, `GET /users?limit=100&offset=0`, `GET /users/{id}`. Minimal reviewer identity; the
hackathon build has no authentication.

## Health and files
`GET /health` -> `{"status":"ok","database":"ok","models":{...}}` or 503 when the database is down.
Uploaded files are served read-only from `/files/...`.

## Errors
`{"detail":"message"}` with 400 (bad input), 404 (missing), 409 (database constraint violation),
413 (upload too large), 422 (validation), 500 (unexpected), 503 (database unavailable).

## Gemini AI assistant
The AI endpoints are optional and disabled unless `AI_ENABLED=true` and a server-side
`GEMINI_API_KEY` are configured. They retrieve from the existing CLIP, MiniLM and PostgreSQL
services before sending a bounded context to the configurable Gemini Flash model. AI output is an
interpretation of retrieved records, not a verification layer; original notes, attribution and
tag provenance remain authoritative.

### GET /ai/status
Returns provider configuration without exposing credentials:
```json
{"enabled":true,"provider":"gemini","model":"gemini-3-flash-preview","configured":true,"available":true}
```
`configured` is false when the API key is absent. `available` reflects local configuration only;
generation can still fail due to provider quota or access restrictions.

### POST /ai/chat
Request:
```json
{
  "question":"Explain the stepwell architecture at Rani ki Vav",
  "history":[{"role":"user","content":"What is special about it?"}],
  "site_id":1,
  "image_id":null
}
```
`question` is limited to 2,000 characters. History is limited to the last ten messages and each
message to 2,000 characters. The response includes `response`, `intent`, real `sites`, real
`images`, `sources`, `ai_generated`, and `warnings`.

### POST /ai/explain/{site_id}
Generates a grounded explanation for an existing site. Unknown sites return 404. The response
includes the real site record, generated explanation, available source references, and warnings.

### POST /ai/trails/suggest
Request:
```json
{"site_ids":[1,2,18],"title":"Stepwells of Gujarat","description":null}
```
Only existing site IDs are accepted. The response contains real site IDs in a suggested order,
a generated theme and rationale, available coordinates, straight-line distance legs, and
missing-coordinate warnings. It does not persist a trail.

Gemini failures are returned as warnings and never trigger a paid fallback or automatic model
switch. Free-tier quotas and model availability are controlled by Google and can change.
