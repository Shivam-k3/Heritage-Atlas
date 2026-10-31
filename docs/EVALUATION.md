# Evaluation plan and report template

Owner: ML lane. Numbers come only from scripts in `backend/scripts/eval_*.py`. Never invent or round up results.

## A. Tagging
- Data: 30-50 hand-labelled photos, split into tune (about 40%) and test (about 60%).
- Tune `FEATURE_THRESHOLD` and prompts on the tune split only.
- Report on the test split: precision, recall, F1 per tag and macro average; confusion list.
- Compare prompt variants (generic vs heritage-specific wording).

## B. Search
- 10-15 queries (e.g. "carved pillars in stepwells", "geometric stone carvings", "ancient water structures", "domed temple architecture").
- Judge top-5 results as relevant or not; report precision@5 for text-to-image and image-to-image.
- Record the judge (a person) and the criteria used.

## C. Verification statistics
Tags generated, reviewed, confirmed, rejected, added by humans, by tag. These are review statistics, not model accuracy.

## D. Failure analysis
Examples where: carvings confused with other features; low-quality photos; similar styles giving irrelevant results; short descriptions.

## Report table (fill in)
| Metric | Value | Dataset size | Notes |
|---|---|---|---|
| Tagging macro F1 (test) | | | |
| Precision@5 text-to-image | | | |
| Precision@5 image-to-image | | | |
| Median search latency | | | |
