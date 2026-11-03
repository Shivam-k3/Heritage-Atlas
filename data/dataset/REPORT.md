# Dataset report

Generated from `data/dataset/manifest.json` and `validation.json`. These are dataset facts, not model metrics.

## Summary

| Item | Value |
|---|---|
| Sites | 30 |
| Images | 150 |
| Unique images | 150 |
| Total size | 114.3 MB |
| Validation errors | 0 |
| Validation warnings | 0 |

## Sites by region

| Region | Sites |
|---|---|
| Gujarat | 15 |
| Rajasthan | 15 |

## Sites by category

| Category | Sites |
|---|---|
| fort | 8 |
| haveli | 2 |
| mosque | 3 |
| palace | 7 |
| stepwell | 4 |
| temple | 6 |

## Images by licence

| Licence | Images |
|---|---|
| CC BY 2.0 | 7 |
| CC BY 3.0 | 9 |
| CC BY-SA 2.0 | 11 |
| CC BY-SA 2.5 | 1 |
| CC BY-SA 3.0 | 76 |
| CC BY-SA 4.0 | 38 |
| CC0 | 3 |
| No restrictions | 3 |
| Public domain | 2 |

## Images per site

| Site | Region | Category | Images |
|---|---|---|---|
| Rani ki Vav | Gujarat | stepwell | 5 |
| Adalaj Stepwell | Gujarat | stepwell | 5 |
| Sun Temple, Modhera | Gujarat | temple | 5 |
| Sidi Saiyyed Mosque | Gujarat | mosque | 5 |
| Bhadra Fort | Gujarat | fort | 5 |
| Lakhota Palace | Gujarat | palace | 5 |
| Prag Mahal | Gujarat | palace | 5 |
| Aina Mahal | Gujarat | palace | 5 |
| Vijay Vilas Palace | Gujarat | palace | 5 |
| Uparkot Fort | Gujarat | fort | 5 |
| Sarkhej Roza | Gujarat | mosque | 5 |
| Hutheesing Jain Temple | Gujarat | temple | 5 |
| Kalika Mata Temple, Pavagadh | Gujarat | temple | 5 |
| Jami Masjid, Champaner | Gujarat | mosque | 5 |
| Somnath Temple | Gujarat | temple | 5 |
| Chittorgarh Fort | Rajasthan | fort | 5 |
| Kumbhalgarh Fort | Rajasthan | fort | 5 |
| Chand Baori | Rajasthan | stepwell | 5 |
| Panna Meena ka Kund | Rajasthan | stepwell | 5 |
| Jaisalmer Fort | Rajasthan | fort | 5 |
| Mehrangarh Fort | Rajasthan | fort | 5 |
| Amber Fort | Rajasthan | fort | 5 |
| Hawa Mahal | Rajasthan | palace | 5 |
| City Palace, Jaipur | Rajasthan | palace | 5 |
| Umaid Bhawan Palace | Rajasthan | palace | 5 |
| Junagarh Fort | Rajasthan | fort | 5 |
| Patwon Ki Haveli | Rajasthan | haveli | 5 |
| Nathmal Ki Haveli | Rajasthan | haveli | 5 |
| Ranakpur Jain Temple | Rajasthan | temple | 5 |
| Dilwara Temples | Rajasthan | temple | 5 |

## Source

Images were downloaded from Wikimedia Commons at thumbnail width 1600 px. Each image row keeps its original file page, author, licence and source URL. Raw images are not committed; rerun `python -m scripts.dataset.download_wikimedia` to recreate `data/raw/`.
