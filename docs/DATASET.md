# Dataset

Theme: Gujarat heritage architecture with selected Rajasthan examples.

## Delivered dataset (31 Oct 2026)
| Item | Value |
|---|---|
| Sites | 30 (15 Gujarat, 15 Rajasthan) |
| Images | 150 (5 per site), 150 unique |
| Size | 114.3 MB |
| Validation | 0 errors, 0 warnings |
| Licences | CC BY 2.0/3.0, CC BY-SA 2.0/2.5/3.0/4.0, CC0, No restrictions, Public domain |
| Metadata | Author, licence, licence URL, source URL, original dimensions, local path |

Committed: `data/dataset/manifest.json`, `sites.json`, `images.json`, `validation.json`, `REPORT.md`,
`data/sites.csv`. Raw images in `data/raw/` are gitignored and reproducible from Commons.

Four sites had no usable Wikipedia extract and were enriched from Wikidata descriptions; the source
is recorded per site in the manifest.

## Rules
1. Check the licence of every image individually. Record author, licence and source URL at download
   time. `scripts/dataset/validate_images.py` rejects rows without them.
2. Prefer Wikimedia Commons files with a clear licence; add our own photos where available.
3. Do not use an image without a recorded licence. Remove it if the licence is unclear.
4. One canonical coordinate per site; verify against OpenStreetMap.
5. Keep original descriptions; note the source of each. AI never overwrites them.

## Pipeline
    python -m scripts.dataset.download_wikimedia   # Commons API -> data/raw
    python -m scripts.dataset.generate_metadata    # -> data/sites.csv + JSON
    python -m scripts.dataset.validate_images      # -> validation.json
    python -m scripts.dataset.generate_report      # -> REPORT.md

`download_wikimedia.py` requests a 1600 px thumbnail (the API returned about 1920 px) and records
the original file page, author, licence and dimensions. It skips images already on disk, so reruns
are safe. `generate_metadata.py` is idempotent after manifest edits.

Roboflow is optional: `python -m scripts.dataset.download_roboflow` skips cleanly unless
`ROBOFLOW_API_KEY`, `ROBOFLOW_WORKSPACE`, `ROBOFLOW_PROJECT` and `ROBOFLOW_VERSION` are set.

## Evaluation split
The split is by site, never by photo: a site's five photos always land in the same split. `site_id`
is hashed to a stable 60/20/20 train/tune/test bucket (`app/services/evaluation.py`), so adding
images later does not move a site between splits. With 30 sites that is about 15 train, 11 tune and
4 test sites (~20 test photos). Treat any result as exploratory, not as evidence of generalisation.

Label 30-50 photos by hand with `eval_tagging.py --template`, using only the seven-label prompt
vocabulary or `none`. Never derive labels from CLIP scores or existing auto tags. Tune per-label
thresholds on tuning sites only (`tune_tagging.py`); never touch the test sites. File formats and
the full workflow are in `docs/EVALUATION.md`.
