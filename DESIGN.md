# DESIGN.md: Heritage Atlas UI design system

Read this before writing any frontend code. Follow it exactly; if something is missing, extend this file first.

## 1. Subject and job
Heritage Atlas is a working tool for people who document stone architecture (stepwells, forts, temples) and for
visitors exploring it. Primary job: **find a place, trust what you are told about it, and follow a journey.**
The design borrows from its subject: stepwell geometry (descending steps, deep shade, water at the bottom),
indigo-dyed textile blues, and limestone.

## 2. Memorable element
**The stepped trail.** A trail's stops are drawn as descending steps, like a cross-section of a stepwell,
with distance between stops on each tread. It appears on the trail page and as a miniature in trail cards.
Everything else stays quiet. Do not add other decorative motifs.

## 3. Provenance is the core UI idea
Every piece of information shows which of three layers it belongs to. Never rely on colour alone.

| Layer | Look | Label text |
|---|---|---|
| Original source (notes, photo, attribution) | Plain text; field notes sit under a 3 px sandstone left rule | "Field note", "Photo by ..." |
| AI-suggested | Dashed 1.5 px amber outline, transparent fill, sparkle icon | "Suggested" |
| Human-verified | Solid teal fill, white text, check icon | "Verified" |
| Added by a reviewer | Solid 1.5 px teal outline, person icon | "Added" |
| Rejected (review and history views only) | Grey text, strikethrough | "Rejected" |

Generated text (e.g. trail journal summaries) carries a "Generated" chip and always sits next to, never in place of, the original note.
Scores are shown as raw similarity with a tooltip: "Similarity to the label, not a probability."

## 4. Colour tokens
| Token | Hex | Use |
|---|---|---|
| `--stone` | #171815 | page background (charcoal) |
| `--paper` | #22231F | panels, inputs |
| `--ink` | #F7F2E8 | body text |
| `--indigo` | #B66B4E | primary actions, headings, selected map pin |
| `--sandstone` | #5D5E57 | rules, field-note bar, borders |
| `--water` | #6FAF8E | verified, success |
| `--turmeric` | #8A5A00 | AI-suggested text and outline (decorative fill #D49A1E) |
| `--clay-red` | #9B2C2C | errors and destructive actions |
| `--mute` | #5E6472 | secondary text |
Contrast: text and interactive elements must reach 4.5:1 (3:1 for large text and icons). Check with a tool; adjust the hex here, not locally.
Dark mode is not in the MVP.

```css
:root{--stone:#171815;--paper:#22231F;--ink:#F7F2E8;--indigo:#B66B4E;--sandstone:#5D5E57;
--water:#6FAF8E;--turmeric:#8A5A00;--clay-red:#E7AE98;--mute:#B8B3A7;}
```

## 5. Typography
| Role | Family | Notes |
|---|---|---|
| Headings, site names, journal titles | Spectral (serif), 600 | give serif text slightly more line height |
| Body, controls, data | Public Sans, 400/600 | |
| Gujarati / Devanagari fallback | Noto Sans Gujarati, Noto Sans Devanagari | declare in the font stack |
Scale (px / line height): 13/18 caption, 15/22 small, 17/27 body, 22/30 h3, 28/36 h2, 38/46 h1. Sentence case everywhere.
No all-caps labels, no tracked-out eyebrow text above headings. Line length at most 70 characters.
Numbers in tables and distances use tabular figures.

## 6. Shape, spacing, depth
- Spacing scale 4, 8, 12, 16, 24, 40, 64.
- Radius by role: photos 0, controls and chips 6, floating map panels 10. Cards are not a default container; use rules and spacing, and use a bordered panel only when content is genuinely separate (a trail, a review item).
- Panels have one 1 px sandstone border; no stacked soft shadows. One shadow level only for floating map controls.
- Section dividers on key pages use a stepped notch (a 2-step stair profile) in sandstone; elsewhere use plain 1 px rules.

## 7. Layout
Map first. On desktop a 400 px left panel (search, filters, results) beside a full-height map. Selecting a pin flies the map and opens the site as a slide-over in the left panel. On mobile the map is full screen with a bottom sheet (peek, half, full).

```
Desktop                                   Mobile
+--------------+------------------------+ +----------------------+
| search  [pic]| map                     | | map                  |
| filters      |      o   o              | |        o   o         |
| results      |   o     o (selected)    | +----------------------+
| (left aligned|                          | | bottom sheet: search |
|  list)       |  zoom/locate controls   | | results / site       |
+--------------+------------------------+ +----------------------+
```
Content is left aligned. Photos lead on site pages: a large main photo, then a gallery that keeps each photo's native aspect ratio in a masonry layout, with attribution under each photo.

## 8. Screens
1. **Explore** (home): map, filters (region, type, feature, verified only), result list. Page loads straight into the map; no hero banner.
2. **Search**: one input with a text/photo toggle. Photo mode accepts drag-and-drop or camera upload. Results are photos with site name, region, matching tags, and a one-line reason ("Matches: carved pillars, stepwell").
3. **Site**: photo gallery, original field note, tags grouped into Site type and Features with provenance chips, per-photo licence line, related sites with "Why related" (shared tags and the matching photo pair), "Add to trail".
4. **Upload**: one form: photos, site (existing or new), field note, location (map pin, place search, or EXIF), author and licence. Progress for each photo shows Uploaded, Analysing, Ready to review.
5. **Review**: photo on the left, suggested tags on the right sorted by lowest similarity first; per tag buttons "Confirm", "Reject", and "Add tag". Keyboard shortcuts: C confirm, R reject, arrow keys to move.
6. **Trails**: list, builder (add sites, drag to reorder, date and note per stop), and trail page with the stepped route, map line, summary and journal.

## 9. Components
Site pin (glyph differs by type, not only colour), cluster, result row, photo tile, provenance chip, tag group, score meter (thin bar plus number), filter bar, search box with mode toggle, upload dropzone, review item, trail stop, stepped route, journal entry, toast, skeleton, empty state, error panel.
Every component defines: default, hover, focus-visible, disabled, loading, error. Focus ring: 2 px indigo with 2 px offset.

## 10. Motion
- One orchestrated moment: when a trail opens, its steps draw in from the top and the map line draws behind them (about 600 ms).
- Responsive motion: map fly-to on pin select, panel slide-over, chip state change.
- Nothing else animates. Respect `prefers-reduced-motion` by replacing motion with instant changes.

## 11. Writing
Plain verbs, sentence case, specific. An action keeps one name through the flow.
| Action | Button | Confirmation |
|---|---|---|
| Upload | "Upload photo" | "Photo uploaded. Analysing now." |
| Review | "Confirm", "Reject", "Add tag" | "Tag confirmed." |
| Trail | "Create trail", "Add to trail" | "Added to Gujarat Stepwell Trail." |
Empty: "No sites match these filters. Clear a filter or upload a photo of a site." Errors name the problem and the fix:
"Couldn't read GPS from this photo. Click the map to set the location." Errors do not apologise or blame.

## 12. Accessibility and quality floor
Keyboard reachable everywhere, visible focus, labelled controls, alt text from the site name and top tag, map has a list alternative, touch targets at least 44 px, readable at 200% zoom, works at 375 px wide.

## 13. Implementation notes
- Tailwind theme extends the tokens above; no raw hex in components.
- Leaflet + OpenStreetMap tiles with attribution visible. Marker clustering enabled.
- All data comes from the API; no hardcoded demo content in the UI.
- Every fetch shows loading, error and empty states.
- Do not use: cream background with terracotta accent, near-black with neon accent, identical rounded cards with the same shadow, gradient wash backgrounds, all-caps eyebrow labels, arrows appended to links.
