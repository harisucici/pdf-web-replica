# Fidelity loop

[中文](../docs/zh/references/fidelity.md) | [English](fidelity.md) | [日本語](../docs/ja/references/fidelity.md)

## Target and division of work

The target is the source page, not a generic reader theme. `build` extracts an initial draft; the agent must analyze, reconstruct, inspect and correct it. These scripts do not turn arbitrary scans into finished layouts automatically. Work continues while a concrete correction is executable. If a missing font, unreadable source or unavailable browser/OCR prevents further progress, preserve the page ledger and report the specific residual and recovery route. Do not hide the issue behind a success message.

Never reuse another document's hand-tuned layout as though it were a general PDF converter. You may reuse drawing techniques and a reader shell. For each new PDF, derive page sizes, families, colors, regions and typography from its actual pages.

## 1. Inventory and source analysis

After building the complete requested range:

```sh
python scripts/run.py analyze outputs/book
```

- `analysis/contact-*.jpg` gives a source-page overview, 24 pages per sheet.
- `analysis/00001.json` contains source palette and connected-color region/rule candidates in displayed PDF coordinates. It does not recognize fonts, infer rounded corners or prove a region is a rectangle. Text holes, photos and gradients can distort candidates. Inspect them before reconstruction; never turn glyph components into traced text.
- `reconstruction-plan.json` tracks every selected page, tentative families and tasks. `family_override` and `notes` preserve manual decisions. Family similarity is a hint; differing headings, tables, footers, colors and page exceptions still need individual checks.

Handle layouts family by family, then check every page. Use source structure to separate panels, columns, table cells, diagrams, illustrations, body text and annotations. Identify hidden OCR, hybrid pages and image tiles. Source-page references stay outside normal published content.

## 2. Reconstruct and synchronize

For native pages, retain text baselines, vectors, fonts and legitimate illustrations where valid. Inspect unsupported clipping, transparency, annotations, Type 3 fonts and font mappings. For scans, combine coordinate OCR with independent CSS/vector regions. Rebuild the missing panels and rules; removing a scan image alone is not reconstruction.

Use page JSON or a patch:

```sh
python scripts/run.py apply-layout outputs/book --page 12 --json work/page-12-layout.json
python scripts/run.py refresh outputs/book
```

A patch may contain `blocks`, `text`, `shapes`, `images`, `web_layout`, `background_color`, `reference_image`. It cannot set review flags. Use `web_layout: null` explicitly to switch back to the generic SVG renderer. Changed content resets review. If OCR/text changes while a manual layout is retained, `layout_needs_sync` blocks acceptance until both representations are updated with `apply-layout`. Keep the visible text, `blocks`, extracted text and search index consistent.

Work at the source scale. Match fills and strokes, corner radii, spacing, line heights, baselines, kerning, width, weight, italics, underlining, vertical/RTL layout and overlap. For ruby/superscripts, enlarge the source crop and transcribe only what exists. Verify fonts by actual glyphs and line lengths; do not claim identical fonts based only on a family name. Unsupported original fonts and unresolved substitutions remain explicit issues.

## 3. Capture real default web pages

Refresh creates `qa/capture-requests.json`, containing each page's current `render_fingerprint`, relative URL and screenshot/metadata filenames. Serve the site locally when the host needs HTTP. Use the host's real permitted browser tool; discover its actual interface. A separate OCR skill is unnecessary, but a vision-only tool that reads images is not automatically a browser renderer.

Navigate to `index.html?qa=1#page=12`. This page-only mode hides the reader shell and uses one CSS pixel per PDF point. Wait for `#paper[data-qa-ready="true"]`, then read and parse the JSON text in `#pdf-replica-qa`. This works even when the host exposes only a read-only DOM scope; `window.PDF_REPLICA_QA` is also available when permitted. It waits for fonts, HTML images and animation frames. The record contains:

```json
{
  "page": 12,
  "render_fingerprint": "copy from the actual ready page",
  "default_view": true,
  "page_only": true,
  "ready": true,
  "visible_text_elements": 42,
  "paper_bbox": {"x": 0, "y": 0, "width": 612, "height": 792}
}
```

Capture the actual page crop specified by `paper_bbox`, not the viewport with toolbars or surrounding margins. Account for the tool's documented CSS/device pixel convention. Save as `work/browser-captures/00012.png` (JPEG also supported). Save the actual ready record as `00012.json`, adding `captured_with` describing the real tool and capture method. Do not write `ready: true`, counts or fingerprints by guessing. Capture all requested pages, using bounded batches if needed.

Never use the PDF reference PNG, the reader's source comparison mode, a screenshot-backed page, or synthetic comparator fixtures as real web capture evidence. The zero score from comparing an image to itself is meaningless. If actual browser capture is unavailable, keep visual evidence pending and diagnose that specific capability; do not invent an unavailable tool or approve layout anyway.

## 4. Compare, diagnose, correct, repeat

```sh
python scripts/run.py compare outputs/book --captures work/browser-captures
```

Optional `--pages 12-24` supports batches. Every requested result is recorded, including missing/invalid captures. Per-page files in `qa/comparisons/` include side-by-side, 50% overlay, difference mask and JSON metrics/worst regions. Captures are copied into `qa/captures/` and bound to current content and source hashes.

The capture must match page aspect ratio. Only the source reference is resampled to the capture's scale; the screenshot is never stretched to disguise geometry differences. The diagnostic defaults are maximum channel difference 24, changed-pixel ratio ≤ 0.01, normalized mean error ≤ 0.005 and worst 1/64-page tile ratio ≤ 0.10. These are strict diagnostics, not a "99% faithful" promise. Small wrong characters can fall below those limits, so text/language/source review remains separate. Do not loosen thresholds just to pass.

Inspect the largest-error areas, then small text at sufficient scale. Fix the cause rather than shifting the whole page blindly: page crop/scale, missing fills, misplaced panels, font metrics, baselines, line breaks, characters, annotations, masks or artwork. Refresh, recapture affected pages, compare again. Recheck each reused layout's exceptions. Browser functionality alone is not visual acceptance. Global low error does not excuse a locally wrong table or lost ruby.

## 5. Record current review and audit

Only after actual source checks:

```sh
python scripts/run.py review outputs/book --pages 12 --checks text,layout,fonts,languages --note "Checked current source/web comparison, text and all flagged areas"
python scripts/run.py audit outputs/book
```

Layout/font review requires current comparison evidence within the diagnostic limits. Review fingerprints cover page content, font/artwork bytes and actual viewer HTML/CSS/JS. Cache-busting timestamps are normalized; real changes invalidate proof. Changed screenshots or references invalidate their evidence too. Boolean flags from older output are insufficient. Blank pages also require source/visual confirmation; unresolved OCR or stale manual layout cannot be approved.

The audit passes only with complete requested coverage, current evidence and the four actual review dimensions. Passing means recorded checks are current; it is not an automated proof of perfect semantic or pixel identity. Report all residual differences and actual limitations. The browser/device/OS may rasterize fonts differently; record an irreducible mismatch rather than pretending that the original font was restored.

## Remaining differences

A layout patch may set `remaining_differences` to a list of concise unresolved source differences, including region/page details and the concrete blocker where applicable. These are reported by audit and prevent review approval. After actually resolving an item, update the list through a new patch; never erase it merely to pass. An empty list does not replace browser evidence or source checks. Clear search highlighting before captures; highlighted pages are not the default source-matching view.

For a user-requested partial range, run `audit <output> --allow-range`. Keep the ordinary full-document audit for full-book requests and unfinished processing chunks; do not use this switch to hide omitted requested pages.
