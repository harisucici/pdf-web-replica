# Recovery paths

[中文](../docs/zh/references/recovery.md) | [English](recovery.md) | [日本語](../docs/ja/references/recovery.md)

Accept the PDF request first, inventory what is available, and choose an actual processing route. Do not return a blanket "PDF not supported" before checking. Complete independent pages and files while recording specific blockers. Do not claim that any software can guarantee successful processing of every possible byte stream.

| Condition | Recovery |
|---|---|
| Python/PyMuPDF absent | Bootstrap an isolated environment with `scripts/bootstrap.py`; use its returned interpreter. If installation is unavailable, use a permitted existing PDF tool or the host's document tools and retain the same ledger/schema. |
| Native extraction empty | Render the page, distinguish a blank page from a scan, then OCR. Missing text is not proof of blankness. |
| OCR backend unavailable | Use macOS Vision if available, local Tesseract with the necessary models, an external JSON adapter, or the host's configured vision. Report the missing capability if none is executable. |
| OCR language missing | Install the requested model when permitted, or use another configured backend. Do not silently use English for another script. |
| Wrong password / encrypted PDF | Use an already authorized password via `--password-env`; otherwise identify that the password is required. Do not brute-force or bypass encryption. |
| Corrupt syntax | PyMuPDF attempts its parser's repair. Build also attempts available `qpdf`/`mutool` into a separate working copy. Retain the original. If all readers fail, report the actual errors and request a recoverable source. |
| PDF portfolio / embedded PDFs | Run `attachments input.pdf --out work/embedded`. Inspect `attachments.json`, then batch-process the embedded PDFs required by the user's scope. Extracted names are contained inside the output directory; never execute attachments. |
| XFA / unsupported interactive content | Identify it in inspection. Use an available renderer/exporter that supports that form to obtain a visual snapshot, then reconstruct actual field text and shapes. Standard PDF text extraction does not prove XFA completeness. |
| Huge page or long document | Rendering adapts pixel area to avoid memory exhaustion. Process every requested page incrementally, raise resolution selectively, and resume. Do not impose an arbitrary page-count cutoff or silently skip low-resolution details. |
| Bad CMap / outlined text / Type 3 glyphs | OCR from the render, then rebuild real Unicode. Keep uncertain fonts and vector/text classification flagged. A set of outlined letters is not selectable source text. |
| Complex tables / charts / mathematics | Use native primitives and text when possible; inspect cells, labels, symbols and reading order. Use appropriate domain OCR if configured. A screenshot or plain Markdown table is not a faithful substitute unless the user explicitly accepts it. |
| Browser is white | Check loading/error notice, page script delivery, active-request race, page geometry, and scroll position. A truly blank source page receives its own notice. Test both local and hosted delivery as applicable. |

Tesseract model aliases in the bundled adapter include `en→eng`, `ja→jpn`, `zh→chi_sim`, `zh-hant→chi_tra`, `ko→kor`; other installed model codes pass through. The language list is not a list of the only allowed PDF languages. The external adapter supports other engines and scripts without modifying the core skill.

These are recovery routes, not permission to change sandbox policy, disable safeguards, upload documents to a new provider without authorization, or hide unresolved pages. A host's deliberate tool/skill restrictions remain in force.
