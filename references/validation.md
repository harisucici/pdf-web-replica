# Validation record

Date: 2026-11-15. Host: macOS ARM64. PDF engine tested: PyMuPDF 1.26.5. Tests use synthetic documents, not user PDFs. No book content, source scans, credentials or extracted source fonts are distributed in the package.

## Processing regression checks — passed

- Native selectable Unicode, including Japanese and Korean.
- Independent illustration extraction and exclusion of a full-page scan from normal web content.
- Actual blank-page classification.
- Rotated page dimensions and text orientation.
- Form values without duplicated appearance text.
- Scan and hybrid pages retained as pending OCR when no backend is selected; a long native header does not falsely establish scanned-body coverage.
- Resume preserves manual corrections; explicit reprocessing affects its selected range.
- Encrypted PDF with an authorized password; missing-password diagnosis and no password in output metadata.
- Malformed-input diagnosis, with batch processing continuing across other files.
- Embedded-PDF attachment extraction.
- Normalized OCR import coordinates.
- Audit refuses unfinished source verification and an empty zero-page ledger.
- macOS Vision with separate English/Japanese/Korean passes.
- External OCR command adapter, including paths containing spaces.

The executable regression suite is `scripts/selftest.py`. Its macOS run completed successfully with the Vision option. The zero-page audit check was also exercised separately.

## Hermes — actual local validation passed

The installed Hermes CLI listed `pdf-web-replica` as **local / enabled**. Its own bootstrapped runtime invoked `tools.skills_tool.skill_view` and loaded the installed skill. A second check ran PDF inspection through the package's interpreter dispatcher from that Hermes runtime and correctly read a five-page mixed PDF. This checks real registration, loading and execution; it does not claim that an LLM has manually verified every possible document.

## Installation and browser checks — passed

The installers for Hermes, Codex, OpenCode and OpenClaw copied the complete package into isolated test roots. Hermes and Codex were additionally installed in their local user skill directories. OpenCode and OpenClaw runtimes were not installed on the test host, so no runtime invocation is claimed for those two; their adapters follow the linked official discovery formats.

A real browser displayed the generated native-text fixture with readable English/Japanese/Korean, one form value, independent graphics, a blank-source notice and correctly oriented rotated text. The rendered normal page had genuine DOM text and no source-page bitmap. Navigation returned to the top. Python syntax, JavaScript syntax and the skill-creator frontmatter validator passed.

## What these checks do not prove

They do not certify pixel identity for arbitrary PDF layouts, universal OCR accuracy, original-font recovery from scans, or successful processing of corrupt/encrypted files without recoverable bytes/passwords. All generated documents begin in draft state and retain a page-by-page acceptance ledger. Cross-platform format compatibility is separate from the availability of a particular OCR engine or host permission.
