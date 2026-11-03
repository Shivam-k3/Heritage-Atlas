# Evaluation plan and status

Owner: ML lane. Numbers come only from scripts in `backend/scripts/`. Never invent, estimate or
round up a result. Scores are raw CLIP cosine similarities, not probabilities.

## Current status (2 Nov 2026, Phase 1)
- Hand feature labels: **not collected**. `data/dataset/tag_annotations.csv` does not exist, so
  per-feature precision, recall, macro/micro-F1 and confusion are **not measured**.
- Per-label acceptance thresholds: **unset** in `app/feature_prompts.json`. Until a human fills
  the tuning rows, the worker emits no auto feature tags rather than forcing a prediction.
- Few-shot probe: framework implemented (`eval_fewshot.py`), but there are not enough explicit
  verified/rejected decisions for a meaningful comparison. No quality claim is made.
- Relevance judgements for search: **not collected**, so precision@5 is **not measured**.
- Review statistics are review counts, not accuracy (`eval_review_stats.py`).
- Checkpoint latencies from 31 Oct 2026 (warm models, single query): text search 101 ms,
  text-to-image 103 ms, image-to-image 264 ms. These are single-query timings, not a benchmark.

## A. Feature annotations
Create the sheet from database metadata, then fill it by hand **before** looking at model output:

    python backend/scripts/eval_tagging.py --template

Columns:

    image_id,site_id,image_path,site_category,expected_features,annotator,annotation_date,split
    4,1,uploads/ab/abcd.jpg,stepwell,sculptural carvings|jali work,asha,2026-11-02,train
    5,1,uploads/cd/cdef.jpg,stepwell,none,asha,2026-11-02,train

- `expected_features` is a pipe-separated list from the prompt vocabulary.
- Use `none` when a photo genuinely shows none of the features.
- Leave `expected_features` empty only while the row is unlabeled.
- Do not derive labels from CLIP scores, existing auto tags or review status. That would leak the
  model into its own evaluation.
- `site_category` is database metadata, not an AI prediction.
- `split` is derived deterministically from `site_id` (60/20/20 train/tune/test). All photos from a
  site stay in the same split.

With 30 sites the realised split is roughly 15 train, 11 tune and 4 test sites, i.e. about 20
held-out test photos. Treat every number as **exploratory**, not evidence of generalisation.

## B. Tagging evaluation
    python backend/scripts/eval_tagging.py

The script compares, on identical held-out test sites:
1. **baseline**: the old nine-feature vocabulary, one generic prompt per feature, universal 0.22
   cut-off, max four tags, plus forced site type (site type is excluded from the feature metrics);
2. **revised**: seven features, four prompt variants aggregated by mean then renormalised;
3. **negative**: revised scores minus per-feature negative-prompt similarity.

Thresholds for (2) and (3) are tuned only on tuning-site human labels by
`scripts/tune_tagging.py`; the test split is never used for tuning. Negative prompts are kept only
if validation improves, so the script reports the comparison rather than assuming subtraction is
valid. Output: `data/dataset/eval_tagging.json` with per-label precision/recall/F1/TP/FP/FN,
macro-F1, micro-F1, false-positive frequency, no-confident-feature frequency and predicted-label
counts. If the annotation sheet is missing, the script reports `not_measured` and exits non-zero.

Tune and record thresholds with:

    python backend/scripts/tune_tagging.py --write

This updates the `threshold` fields in `app/feature_prompts.json` (v2) and writes
`data/dataset/tagging_thresholds.json` with the tuning sites, image count and prompt/model
version. A label with no positive tuning example stays `null` and can never be emitted.

## C. Few-shot logistic-regression experiment
    python backend/scripts/eval_fewshot.py

- Uses CLIP image embeddings only.
- Positives: `verified` and `added_by_human`; negatives: explicit `rejected`. Unreviewed auto tags
  and images without a decision for a label are excluded, never treated as ground truth.
- Site-wise split identical to the zero-shot evaluation; `StandardScaler` and the L2 logistic
  regression are fit on training sites only.
- Compares per-label metrics and macro-F1 with the revised zero-shot system on the same held-out
  sites, and reports sample counts and class imbalance.
- If the minimum per-class counts are not met, the report says `insufficient_labels` and the
  comparison is not statistically meaningful.

## D. Search
- 10-15 queries; a human judges top-5 results as relevant or not.
- Report precision@5 for text-to-image and image-to-image.
- Judgement file: `data/dataset/search_judgements.json`:

    {
      "text_queries": [
        {"query": "carved pillars in stepwells", "relevant_image_ids": [4, 6, 7]}
      ],
      "image_queries": [
        {"image": "data/raw/rani-ki-vav/1.jpg", "relevant_image_ids": [4, 6]}
      ]
    }

    python backend/scripts/eval_search.py

## E. Verification statistics
    python backend/scripts/eval_review_stats.py

Counts generated/reviewed/confirmed/rejected/added tags by label. These are review statistics, not
model accuracy.

## Report table (fill in only from the scripts)
| Metric | Value | Dataset size | Notes |
|---|---|---|---|
| Tagging macro F1 (test, baseline/revised/negative) | not measured | 150 images | no hand labels |
| Tagging micro F1 and no-confident frequency | not measured | 150 images | no hand labels |
| Few-shot probe macro F1 vs zero-shot | not measured | reviewed tags only | insufficient explicit decisions |
| Precision@5 text-to-image | not measured | 150 images | no relevance judgements |
| Precision@5 image-to-image | not measured | 150 images | no relevance judgements |
| Median search latency | 101 ms text, 103 ms text-to-image, 264 ms image-to-image | 150 images | warm models, single query, 31 Oct 2026 |

## F. Failure analysis
The pre-fix run over-tagged generic features (`jali work` on 143/151 images, `staircases` on
90/151). That is the reason the revised system has per-label cut-offs, no forced site type and a
seven-label vocabulary. The exact post-fix false-positive rate is unknown until labels exist.
