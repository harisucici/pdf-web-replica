# Page and OCR schema

[中文](../docs/zh/references/page-schema.md) | [English](page-schema.md) | [日本語](../docs/ja/references/page-schema.md)

`<output>/manifest.json` records the source hash, total page count, processed range and every page's state. Per-page editable files are in `<output>/pages/00001.json`. `site/pages/*.js` are generated output; edit the JSON, then run `refresh`.

## OCR import

```json
{
  "coordinate_space": "normalized",
  "blocks": [
    {
      "text": "Exact source text 한국어 日本語 中文",
      "bbox": [0.12, 0.18, 0.84, 0.21],
      "language": "ko",
      "confidence": 0.94
    }
  ]
}
```

Bounding boxes are `[left, top, right, bottom]`, with a top-left origin. `normalized` uses 0–1; `pixels` also requires `width` and `height` for the OCR image; `pdf` uses points in the displayed page coordinate system. All coordinates refer to the **rotated, cropped rendered page**, not an uncropped PDF media box. Importing OCR replaces that page's text blocks and clears its review flags. Preserve native/form blocks explicitly if needed in a hybrid page.

`blocks` support `text`, `bbox`, `origin` (baseline), `font_size`, `font_family`, `font_file`, `advance`, `angle`, `color`, `bold`, `italic`, `language`, `rtl`, `source`, and `role`. Native fields retain field names/types; checkbox/radio snapshots are rendered as shapes. Complex forms still need validation.

`shapes` are independent SVG drawing elements: `path`, `fill`, `stroke`, `width`, `fill_opacity`, `stroke_opacity`, `even_odd`. A rectangle can be represented as `M 40 50 H 220 V 120 H 40 Z`. Never supply a path traced from source word shapes as a replacement for real text.

`images` contain `file` relative to `site/`, plus `bbox` or a six-number affine `matrix` mapping a unit square to page coordinates. Use this only for isolated illustrations/logos/photos, not page screenshots or text paragraphs. Native extraction writes content-hashed assets.

States: `blank` means the source page is truly blank; `needs_ocr` means unresolved text, `error` means a processing failure, and `draft` means data exists but source verification is incomplete. Review flags `text`, `layout`, `fonts`, `languages` start false. Record actual verification through the CLI, with a meaningful note.

## Resumability and publication

The source hash prevents accidentally reusing an output directory for another PDF. Writes are atomic; successful pages are retained when another page fails. Publish only `site/`. `references/`, working OCR files and the source PDF are not included in that directory. If the user requests a reference-comparison feature, add it explicitly as a separate mode and label it; do not use the reference as the normal page background.

## Illustration approval

Newly extracted `images` entries use `role: "illustration_candidate"` and `reviewed: false`. After checking that the asset contains only isolated artwork, set `role: "illustration"` and `reviewed: true`; only these approved entries pass the reader's geometry guard. Legacy entries without these fields are withheld. Bbox and matrix placements are both checked, so inconsistent metadata cannot shrink a large raster's reported footprint. Page scans, large suspicious rasters and jointly page-covering tiles are not normal illustration content. Preserve them only as reference material and rebuild their text/layout.

`excluded_images` records old rejected image descriptors and `exclusion_reason`; it is diagnostic metadata and is never rendered. Refresh resets the four review flags on changed pages while preserving text and manual notes. After actual reconstruction and verification, the normal review workflow can record acceptance; exclusion history alone is not proof that reconstruction has finished.

## Native HTML/CSS layout

For manually reconstructed pages, `web_layout` provides a structured alternative to the generic SVG text blocks. Its `elements` list contains independent `div`, `span`, `svg` and `path` nodes with `style` (CSS declarations), `text`, `attrs` and `children`. Allowed SVG attributes are `viewBox`, `d`, `fill`, `stroke`, `stroke-width`, `stroke-linejoin` and `aria-hidden`. Raw HTML, scripts and CSS URL resources are not supported. Use absolute CSS positions in the page's displayed point coordinates. Raster nodes must be `{ "tag": "img", "image_file": "illustrations/mascot.png" }`; the file must also be an approved entry in `images`. Placement comes from that approved entry's bbox, not arbitrary node styling.

`web_layout.blocks` uses `text`, normalized `x`, `y`, `w`, `h`, point-sized `size`, `font` (`serif`, `sans`, `korean`), `bold` and `color`. Optional `parts` contain `text`, `bold`, `underline`; `rubies` contain `text`, `offset`, `length`; optional `number`, `numberSize`, `numberFont` create a separate number badge. The viewer measures each text run and scales it horizontally to the supplied width. These remain visible selectable HTML spans. Maintain corresponding `blocks`/`text` in the page record for extraction, search and audit; the presence of `web_layout` does not establish fidelity or approval.

`reference_image` optionally names an authorized source-comparison asset relative to `site/`. It is displayed only after the reader's explicit comparison button is pressed, never as the normal page. Do not populate it unless including source reference images in the deliverable is intended. `manifest.json` may set `display_title` and `subtitle` for the reader header. The default interface follows the original two-bar reader, with whole-document search, a text sidebar and page-width controls; each PDF's own colors, panels and typography still require source-driven reconstruction rather than a generic theme.

## Source-bound evidence and layout patches

`background_color` sets the original page fill. `render_fingerprint` is generated by `refresh`; do not invent it. It hashes visible page data, extracted text, font/artwork bytes and viewer templates. `review_signatures` binds each completed check to that version. Boolean flags alone are insufficient. `layout_needs_sync` marks OCR/text updates that have not been reflected in a retained manual layout. Resolve it with a matching `apply-layout` patch; do not clear it to hide stale visible text.

`apply-layout` accepts only `blocks`, `text`, `shapes`, `images`, `web_layout`, `background_color`, `reference_image`, and resets review. Omitted fields are preserved; `web_layout: null` explicitly removes a manual layout. If blocks change without text, text is rebuilt from their contents. See [the fidelity loop](fidelity.md) for screenshot metadata, comparisons and current evidence requirements.

`remaining_differences` is a list of nonempty descriptions of unresolved source mismatches. Layout patches may update it; open items block review and audit. It is diagnostic, not a rendered text layer.
