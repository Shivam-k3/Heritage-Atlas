# Dataset plan

Theme: Gujarat heritage architecture with selected Rajasthan examples.
Target: 20-30 sites, 3-8 photos each (about 100-200 photos), tags for evaluation.

## Rules
1. Check the licence of every image individually. Record author, licence, source URL at download time.
2. Prefer Wikimedia Commons files with a clear licence; add our own photos where available.
3. Do not use an image without a recorded licence. Remove it if the licence is unclear.
4. One canonical coordinate per site; verify against OpenStreetMap.
5. Keep original descriptions; note the source of each.

## Starting list (verify each; not a finished dataset)
Rani ki Vav (Patan), Adalaj Stepwell, Modhera Sun Temple, Dada Hari Ni Vav, Sidi Saiyyed Mosque jali,
Chittorgarh Fort, Kumbhalgarh Fort, Chand Baori, Panna Meena ka Kund, Jaisalmer Fort.

## Tracking sheet (CSV: data/sites.csv)
`site_name,region,category,lat,lon,description,description_source,image_file,author,licence,source_url,labelled_tags`

## Evaluation split
Hand-label 30-50 photos with `labelled_tags` (semicolon separated, from the controlled vocabulary).
Do not tune thresholds on photos reserved for the final reported numbers: split them into tune and test sets.
