# Changelog

[中文](docs/zh/CHANGELOG.md) | [English](CHANGELOG.md) | [日本語](docs/ja/CHANGELOG.md)

## Unreleased

- Continue OCR auto mode through installed fallback routes after failure/empty output; preserve PDF stems and relative folders in batch output. Explicit unresolved source differences block acceptance.

- Develop the 1.1.0 source-driven fidelity loop: region analysis, contact sheets, per-page plans, layout patches, page-only capture readiness, pixel comparison artifacts and version-bound review evidence. Add Pillow and synthetic evidence regressions.

- Restore the original reader interface and add structured native HTML/CSS page layouts, whole-document search, a text sidebar and explicit source comparison.

- Fix margin and tiled scans being extracted as illustrations. Require source-reviewed isolated artwork in the reader, migrate legacy images on refresh, and add extractor/reader regressions.

- Document minimal Hermes client invocation with `/pdf-web-replica`, attachments and file paths.
- Provide Chinese, English and Japanese README, workflow, technical references and changelog, with language navigation.
- Include localized documentation in packages while retaining a single canonical `SKILL.md` entrypoint.

## 1.0.0 — 2026-11-15

- Portable Agent Skills package for Hermes Agent, Codex, OpenCode and OpenClaw.
- PDF inspection, native text/vector extraction, separate multilingual OCR adapters and selectable web output.
- Batch processing, resume, explicit reprocessing, encrypted-file handling, attachment extraction and per-page review records.
- Interpreter dispatcher for agents running in a different Python environment.
- Hermes discovery, skill loading and PDF inspection verified with the installed Hermes runtime.
- Synthetic regression coverage and browser checks; generated documents remain drafts until source verification.

This release does not guarantee perfect OCR or pixel-identical reconstruction of every possible PDF.
