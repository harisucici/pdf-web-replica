# Page and OCR schema

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
