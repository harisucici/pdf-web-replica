# Layout and OCR procedure

## Inventory before layout

Read every page's ledger entry. A document may combine scans, genuine text, pre-existing invisible OCR, vector diagrams, tables, forms, different crop boxes and rotations. Do not extrapolate the first page's format to the whole document. The CLI preserves native vectors, genuine small images and positioned Unicode text where possible, and excludes large page facsimiles. Scan pages still need native layout reconstruction after OCR.

The default output `site/` contains no source-page screenshot backgrounds. Source PNGs are in the separate `references/` directory for comparison. A large legitimate photograph and a text-bearing page scan are not interchangeable; classify and isolate artwork before adding it to `images`. Never trace a page into SVG and call the remaining word outlines independent webpage text.

## Native geometry

Use PDF coordinates in points, normalized to the rendered crop box and rotation. Native text carries a baseline origin, angle, font size and advance. The included viewer renders actual Unicode SVG text, not outlines or a raster canvas; it is selectable web text. If a user requires only HTML text tags, adapt these blocks to positioned HTML spans while retaining baseline and writing direction.

Reuse browser-embeddable source fonts when available. The CLI reports fonts it cannot embed. A subset font may have missing Unicode mappings even when it is technically embeddable; check representative glyphs and then all used characters. Do not declare a replacement font identical. Keep bold, italics, underlines, baseline, kerning, rubies, vertical writing and RTL behavior in the review scope.

Native vector paths are original drawing primitives, not traced scan text. Clipping, blend modes, transparency, patterns, Type 3 fonts and unusual annotations require separate visual checks. The generic extractor is an initial draft, not a complete PDF rendering engine.

## Scans and multilingual pages

1. Render a representative page at adequate resolution and identify all scripts visually. Supply languages explicitly for production batches. `auto` is a diagnostic first pass, not evidence that every language was recognized.
2. macOS Vision and Tesseract adapters run requested languages separately, then perform preliminary spatial fusion. Inspect conflicts. CJK-looking output can be a failed Korean reading, not valid Chinese. Latin characters can also be false matches to kana or diacritics.
3. For another backend, pass `--ocr external --ocr-command-json '["python", "adapter.py", "{image}", "{output}", "{languages}"]'`. Arguments are passed without a shell. The adapter writes the JSON schema in `page-schema.md` to `{output}` or emits JSON to stdout.
4. If no local OCR works, use the host's permitted vision/document tools. Preserve exact source text, language and coordinates. Import results; do not silently replace missing words with invented translations, inferred answers or dictionary-generated furigana.
5. Rebuild colored panels, columns, cells, rules, page labels and accents as independent shapes. Extract only genuine illustrations as individual assets. Keep source-line and paragraph boundaries where they matter; do not compress a whole paragraph into one line just to fit a box.
6. Compare uncertain text with supplementary source layers or appendices, but resolve disagreements against the actual page. Supplemental transcripts may have their own typos and duplicate IDs.

After changing page JSON, run `refresh <output>` to regenerate the viewer and text. `--resume` preserves processed/manual pages. To intentionally rerun an already processed page, use `--resume --reprocess --pages <range>`; this replaces that range and resets its review flags. Keep manual corrections backed up first.

## Acceptance

Open the site in a real browser and compare it with source renders at the same scale. Check all requested pages. Test initial loading, rapid page changes, rotated pages, true blank pages, a long-to-short page change, source-language copy/search, and local `file://` access when that is the delivery method. Navigation must reset scroll; a data load failure must not masquerade as a blank source page.

Complete the four review dimensions only after evidence exists. OCR confidence, page counts, a successful build, an attractive sample or a single screenshot does not prove full-document fidelity. Keep unresolved issues visible in `audit.json` and in the delivery message.
