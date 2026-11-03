# API contracts

Source of truth: `docs/API.md` (behaviour) and `docs/openapi.json` (generated schema, 34 paths).
This page is the quick map used for integration.

| Area | Method | Path | Request | Response |
|---|---|---|---|---|
| Sites | GET | `/sites` | `region`, `category`, `tag`, `verified_only`, `limit`, `offset` | `SiteSummaryOut[]` |
| Sites | POST | `/sites` | `SiteCreate` | `SiteDetailOut` (201) |
| Sites | GET | `/sites/{id}` | - | `SiteDetailOut` |
| Sites | PATCH | `/sites/{id}` | partial `SiteUpdate` | `SiteDetailOut` |
| Related | GET | `/sites/{id}/related` | `k`, `alpha` | `RelatedSiteOut[]` |
| Drafts | GET | `/sites/drafts` | `limit`, `offset` | `DraftSiteOut[]` |
| Drafts | POST | `/sites/{id}/confirm` | - | `SiteDetailOut` |
| Drafts | POST | `/sites/{id}/reject` | - | `SiteDetailOut` |
| Drafts | POST | `/sites/{id}/merge` | `{"target_site_id": int}` | `SiteDetailOut` |
| Upload | POST | `/images/upload` | multipart file + site + licence fields | `UploadOut` (202) |
| Upload | POST | `/images/upload-batch` | repeated `files` + site fields | `UploadBatchOut` (202) |
| Ingest | GET | `/ingest/batches` | `limit`, `offset` | `IngestBatchOut[]` |
| Ingest | GET | `/ingest/batches/{id}` | - | `IngestBatchOut` |
| Images | GET | `/images/{id}` | - | `ImageOut` |
| Images | GET | `/images/{id}/tags` | - | `TagOut[]` |
| Images | POST | `/images/{id}/reprocess` | - | `JobOut` (202) |
| Jobs | GET | `/jobs/{id}` | - | `JobOut` |
| Search | GET | `/search/text` | `q`, filters, `k`, `offset` | `SearchSiteOut[]` |
| Search | GET | `/search/images` | `q`, filters, `k`, `offset` | `SearchImageOut[]` |
| Search | POST | `/search/by-image` | multipart file, filters, `cross_site`, `exclude_image_id`, `max_per_site`, `k` | `SearchImageOut[]` |
| Review | GET | `/review/queue` | `limit`, `offset`, `status` | `ReviewQueueOut[]` |
| Review | GET | `/review/reviewers` | - | `string[]` |
| Review | POST | `/review/tags/{image_tag_id}` | `ReviewAction` | `ReviewResult` |
| Review | POST | `/review/tags/add` | `HumanTagCreate` | `ReviewResult` |
| Review | GET | `/review/history/{image_tag_id}` | - | `ReviewHistoryOut[]` |
| Trails | POST | `/trails` | `TrailCreate` | `TrailOut` (201) |
| Trails | GET | `/trails` | `created_by`, `is_public`, `limit`, `offset` | `TrailOut[]` |
| Trails | GET | `/trails/{id}` | - | `TrailOut` |
| Trails | PATCH | `/trails/{id}` | partial `TrailUpdate` | `TrailOut` |
| Trails | POST | `/trails/{id}/stops` | `TrailStopCreate` | `TrailStopOut` (201) |
| Trails | DELETE | `/trails/{id}/stops/{stop_id}` | - | `TrailStopOut[]` |
| Trails | PATCH | `/trails/{id}/stops/reorder` | `{"stop_ids": [...]}` | `TrailStopOut[]` |
| Trails | POST | `/trails/from-images` | `TrailFromImages` | `TrailFromImagesOut` (201) |
| Trails | GET | `/trails/{id}/summary` | - | `TrailSummaryOut` |
| Trails | GET | `/trails/{id}/journal` | - | `JournalOut` |
| Users | POST/GET | `/users` | `UserCreate` / paging | `UserOut` |
| Users | GET | `/users/{id}` | - | `UserOut` |
| Health | GET | `/health` | - | `HealthOut` or 503 |

Integration notes:
- The frontend contract is `GET /sites` (bare array) and `GET /sites/{id}`; both keep their shape.
- `score` is always a raw cosine similarity. Do not render it as a percentage or confidence.
- Tag `status` is `auto | verified | rejected | added_by_human`; the UI must show provenance.
  Rejected tags are excluded from search hits.
- Image search hits keep `name` for the site name and add `tags`, `author`, `licence`,
  `licence_url`, `source_url`; no field breaks existing consumers.
- Image-to-image adds `cross_site`, `exclude_image_id` and `max_per_site`. The default
  (`cross_site=false`) keeps the old response semantics; `cross_site=true` is the cross-site
  discovery mode.
- Review queue and reviewer endpoints are described in `docs/API.md`; reviewer values are a fixed
  demo list, not authentication.
- Trail stops include `lat`/`lon`; reorder and delete both return the ordered stops with
  `stop_order` renumbered from 1.
- Trail distances are straight-line Haversine only. `TrailSummaryOut.distance_mode` is always
  `"straight_line"` and `missing_coordinates` lists site ids that could not be measured.
- `POST /trails/from-images` derives stops from stored image timestamps and site coordinates.
  It never invents missing GPS or timestamps; `images_used` and `images_skipped` report coverage.
- Trail journal keeps `original_note` and `generated_summary` in separate fields.
