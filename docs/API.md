# API contract

Base URL (dev): `http://localhost:8000`. JSON unless noted. Scores are raw cosine similarities in [-1, 1].
Status: **[done]** implemented in the scaffold, **[todo]** planned. Change this file in the same PR as any API change.

## Sites
### GET /sites [done; filters todo]
Query: `region`, `category`, `tag` (label), `verified_only` (bool).
```json
[{"id":1,"name":"Rani ki Vav","region":"Gujarat","category":"stepwell","lat":23.8593,"lon":72.1018}]
```
### GET /sites/{id} [done]
```json
{"id":1,"name":"Rani ki Vav","region":"Gujarat","category":"stepwell","lat":23.8593,"lon":72.1018,
 "description":"original field note",
 "images":[{"id":4,"url":"/files/abc.jpg","author":"...","licence":"CC BY-SA 4.0","source_url":"...","status":"processed",
   "tags":[{"id":9,"label":"carved pillars","tag_type":"feature","score":0.27,"status":"auto"}]}]}
```
### POST /sites [todo] / PATCH /sites/{id} [todo]
Create or edit a site (name, region, category, lat, lon, description).

## Upload
### POST /images/upload [done] multipart/form-data
Fields: `file`, and either `site_id` or `site_name`; optional `region`, `lat`, `lon`, `description`, `author`, `licence`, `source_url`.
```json
{"site_id":1,"image_id":4,"job_id":7,"status":"queued"}
```
### GET /jobs/{id} [done]
```json
{"id":7,"status":"pending|running|done|failed","error":null}
```
### POST /images/{id}/reprocess [todo]

## Search
### GET /search/text?q=&k=10 [done]  (MiniLM, descriptions)
```json
[{"id":1,"name":"Rani ki Vav","region":"Gujarat","description":"...","score":0.61}]
```
### GET /search/images?q=&k=10 [done]  (CLIP text-to-image)
### POST /search/by-image multipart `file`, `k` [done]  (CLIP image-to-image)
```json
[{"image_id":4,"site_id":1,"name":"Rani ki Vav","region":"Gujarat","url":"/files/abc.jpg","score":0.83}]
```
Filters (`region`, `tag`, `verified_only`) on all three: [todo].

## Related sites
### GET /sites/{id}/related?k=5 [todo]
```json
[{"site_id":2,"name":"Adalaj Stepwell","score":0.74,"clip_similarity":0.81,"tag_overlap":0.60,
  "shared_tags":["stepwell","carved pillars"],"evidence":{"image_a":4,"image_b":11}}]
```

## Review
### GET /review/queue?limit=50 [done]  lowest score first
```json
[{"id":9,"image_id":4,"label":"jali work","tag_type":"feature","score":0.23}]
```
### POST /review/tags/{image_tag_id} [done]
Body `{"action":"confirm|reject","reviewer":"name"}` -> `{"id":9,"status":"verified|rejected"}`
### POST /review/tags/add [done]
Body `{"image_id":4,"label":"domes","reviewer":"name"}` -> `{"id":12,"status":"added_by_human"}`
### GET /review/history/{image_tag_id} [todo]

## Trails [todo]
| Method | Path | Notes |
|---|---|---|
| POST | /trails | `{"title","description"}` |
| GET | /trails | list |
| GET | /trails/{id} | trail with ordered stops |
| POST | /trails/{id}/stops | `{"site_id","visit_date","note"}` |
| PATCH | /trails/{id}/stops/reorder | `{"stop_ids":[3,1,2]}` |
| GET | /trails/{id}/summary | `{"sites":3,"photos":14,"total_km":212.4,"top_features":["carved pillars"],"legs":[{"from":1,"to":2,"km":62.1}]}` |
| GET | /trails/{id}/journal | entries with `original_note` and `generated_summary` as separate fields |

## Errors
`{"detail":"message"}` with 400 (bad input), 404 (missing), 422 (validation), 500 (unexpected).
