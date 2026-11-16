# Source reconstruction quality baseline

[中文](../docs/zh/references/scan-quality.md) | [English](scan-quality.md) | [日本語](../docs/ja/references/scan-quality.md)

Use this procedure for scans, mixed CJK books and source-matching requests. The
baseline is source-positioned visible text plus original cropped artwork, not a
bare OCR viewer. Apply it on every invocation; the user need not request it again.

## Runtime and first pass

```sh
python3 scripts/bootstrap.py --venv work/.pdf-web-env --enhanced-ocr
# Use the returned interpreter for every following command.
<python> scripts/run.py doctor
<python> scripts/run.py build "book.pdf" --out "outputs/book" --languages ja,zh,ko,en --ocr rapidocr
<python> scripts/run.py analyze "outputs/book"
<python> scripts/run.py enhance "outputs/book" --refine-ruby
```

The default render is 216 dpi, bounded for enormous pages. Inspect the embedded
scan's actual resolution; upscaling cannot recover absent detail. The optional
runtime uses local PP-OCRv6 small for Japanese/Chinese/Latin and a separate Korean
PP-OCRv5 mobile recognizer on the same detected regions. Japanese small-annotation
rechecks also use PP-OCRv4. Weights download on first use; documents remain local.
`auto` prefers this route when installed and applicable, then keeps installed
fallbacks. Unsupported languages must use an appropriate alternate route; never
silently discard them. Missing models/runtime are recovery tasks, not permission
to deliver the earlier, visibly inaccurate first pass.

Build retains raw alternatives and character boxes in `work/`; `enhance` writes
source-derived editable geometry, glyph-metric/font candidates and a report.
Native text/fonts/vectors and existing manual `web_layout` are preserved. Original
page JSON is backed up before enhancement. Neither tool approves its own result.

## Text and typography

- Split body text, ruby and other small annotations before choosing font sizes.
  A combined OCR bbox is not the body font's em square. Fit actual ink height,
  baseline and advance using the source crop and real font metrics.
- Compare serif/Mincho, sans/Gothic, weights and Latin/Korean faces on actual
  glyphs. A uniform sans-serif default is insufficient. Font substitutions remain
  explicit; do not embed proprietary system fonts without the appropriate rights.
- Separate upright vertical characters. Use character boxes to split leading
  question/answer numbers from sentences and options; preserve their distinct
  positions/fonts. Do not distribute an intentional large gap across the line.
- `enhance --refine-ruby` re-reads source pixels only. Review its alternatives,
  punctuation, dakuten/handakuten and merged syllables. It never consults a
  dictionary or generates readings. Low confidence is a worklist, not acceptance.
- Korean suffixes on mixed definition lines need their own geometry and font.
  Cross-check alternatives only for the same source line and extent. Reject an
  alternative whose bbox joins adjacent lines; confidence alone cannot justify
  replacing a correct Japanese row with a false Hangul reading.
- For display titles, very large text, reversed text and mixed-font runs, enlarge
  the source and adjust explicitly. Morphological rule removal must not erase
  broad strokes of a large `500`, `N1` or other lettering.

Optional `--font-config work/fonts.json` accepts a list of installed font faces:

```json
[{"path":"/path/to/font.ttc","index":0,"family":"Installed CSS family",
  "languages":["ja","zh"],"bold":false}]
```

## Regions and artwork

Detect distinct source colors separately: a dark-brown heading and gray body must
not merge merely because both fall below one grayscale threshold. Preserve light
sidebars, rounded/notched panels, white table cells, medium-gray number disks,
check boxes, rules and underlines as independent native elements. Palette and
component heuristics can miss these: inspect and correct the page JSON.

Icons, mascots, arrows, logos and illustrations must be cropped from the PDF's
source pixels, with original coordinates, aspect and detail. Do not substitute
emoji, redraw a mascot, use generated artwork, or retain a text-bearing page
image just because it occupies only part of the canvas.

```sh
<python> scripts/run.py crop-artwork outputs/book --page 12 \
  --bbox 95 185 124 215 --reviewed --note "Compared source crop: isolated mascot only"
```

Those coordinates are an example, not a reusable book template. Derive every crop
from the current PDF. The command rejects page-sized/tiled rasters and overlaps
with recognized text. If the drawing was falsely recognized as text, inspect the
source and explicitly correct those blocks first. Never suppress real text to
make the crop pass.

When a genuine illustration encloses a label, remove that label's pixels with
`--exclude-text-bbox x0 y0 x1 y1` (repeatable), retain visible Unicode for it, and
rebuild any flat background behind the transparent hole. Inspect the resulting
asset and page together. `--reviewed` requires actual source inspection and a note;
without it the asset remains an unrendered candidate. Do not auto-approve guessed
connected components or rasterize a paragraph into a purported icon.

## Repeatable acceptance

Before scaling up, correct representative pages from every layout family,
including cover/large text, instructions, question pages, multilingual answers,
reviews and appendices. Reuse techniques and confirmed structures, never literal
text, page dimensions, icon positions or palette values from another book.

Then process the complete range, crop the remaining artwork and compare **every**
default web page at the same scale using [the fidelity loop](fidelity.md). Inspect
worst regions and small characters; test copy, Japanese search, vertical labels,
page changes and local file access. Keep a per-page residual ledger. Recheck after
each correction: content, font and asset changes invalidate old evidence.

The delivery standard is this reconstruction workflow plus actual source review.
It is not an unconditional guarantee that arbitrary damaged scans or unavailable
fonts can be reproduced perfectly. If the baseline is not reached, continue
concrete corrections or report the exact blocked pages/regions; do not silently
downgrade to first-pass OCR or claim a percentage of reconstruction.

For a user-requested partial range, run `audit <output> --allow-range`. Keep the ordinary full-document audit for full-book requests and unfinished processing chunks; do not use this switch to hide omitted requested pages.

The enhanced dependency file pins RapidOCR and OpenCV, and restricts NumPy to the tested ABI range. Native inference runs in a persistent child: a native exit or timeout becomes an ordinary page/backend failure, rather than terminating the whole PDF build. `doctor` lists the installed package versions and model routes; `work/ocr-runtime.json` records model hashes. Use the pinned isolated runtime when recovering `rapidocr_native_worker_exited`, then retry only the affected pages.

Identify each book's actual translation languages before batch OCR. For Japanese/English/Vietnamese editions use `--languages ja,en,vi`; retain Vietnamese diacritics and fit available Latin font faces. Do not enable Korean just because another volume used it. Model support is source-language specific, not a fixed four-language book template.
