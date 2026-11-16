# PDF Web Replica

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

A portable skill for PDF text extraction, OCR and web reconstruction. Supports Hermes Agent, Codex, OpenCode, OpenClaw and other hosts that read Agent Skills folders.

## Installation

After extracting the package, enter `pdf-web-replica` and choose your agent:

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

On Windows, use `py -3` instead of `python3` if needed. When the skill already exists, `--update` preserves a backup. Use `--root "/path/to/skills"` for another Hermes profile or backend. Installation copies files without changing agent settings, models, permissions or security configuration.

To preload the skill for a Hermes session:

```sh
hermes -s pdf-web-replica
```

## Quick client use

After installation, start a new Hermes conversation, attach a PDF and enter only:

```text
/pdf-web-replica
```

Alternatively provide a path directly (quote paths containing spaces):

```text
/pdf-web-replica "/path/to/example.pdf"
```

You do not need to repeat the layout requirements. By default, the skill extracts all text, reconstructs the original layout, styling and background colors using selectable web text, processes every page and compares it with the source. Full-page scans are not the default background. Output goes to `outputs/<original-PDF-filename-without-.pdf>/`. If no file is supplied or several candidates are ambiguous, the agent asks which PDF to use. Unverified work remains a draft rather than being declared a completed faithful replica.

Install in the machine, profile or remote backend that actually runs Hermes. The PDF must be accessible there. A local installation is not automatically synchronized to a remote server.

In other agents, ask to use `pdf-web-replica` and attach a PDF or provide its path. See [agent integration](references/agents.md) for host loading mechanisms. Hermes shorthand follows its [official skills documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills).

The skill imposes no OS, toolset, API-key or PDF-type eligibility gate in Hermes. Scans trigger OCR or configured vision tools rather than a blanket refusal. No software can guarantee success with corrupt files, unknown passwords or unavailable tools; these produce concrete diagnostics rather than fabricated completion.

## Reconstruct and verify against the original PDF

The default goal is the closest achievable reconstruction of the source page, not stopping after OCR. Document colors, regions, typography, spacing, ruby, tables and illustrations must come from the actual PDF. A generic reader interface does not replace source layout. Do not silently rewrite typos that exist in the source.

After the draft, continue with source analysis, reconstruction, real browser captures, difference correction and audit:

```sh
python scripts/run.py analyze "outputs/example"
python scripts/run.py apply-layout "outputs/example" --page 1 --json "work/page-1-layout.json"
python scripts/run.py refresh "outputs/example"
python scripts/run.py compare "outputs/example" --captures "work/browser-captures"
python scripts/run.py audit "outputs/example"
```

`analyze` produces contact sheets, color/line candidates, layout families and page tasks; inspect candidates before use. `compare` uses actual default-web screenshots and generates side-by-side, overlay, difference and worst-region artifacts. Layout/font checks cannot pass without current visual evidence or while substantial differences remain. Edits to pages, fonts, artwork or the viewer invalidate earlier proof. Check every page: pixel metrics are not a reconstruction percentage and cannot excuse small wrong characters.

See [the fidelity loop](references/fidelity.md) for capture metadata, iteration and review commands. Analysis/comparison uses PyMuPDF and Pillow, without a separate OCR skill; executable OCR and browser capabilities come from the host. Scripts assist the agent, which must continue reconstructing the actual pages. They do not guarantee unconditional 100% results for every file.

## Local commands

```sh
python3 scripts/run.py doctor
python3 scripts/bootstrap.py --venv work/.pdf-web-env
```

When an isolated environment is needed, use the Python interpreter returned by bootstrap:

```sh
python scripts/run.py build "example.pdf" --out "outputs/example" --languages ja,zh,ko,en
python scripts/run.py batch "pdf-folder" --out "outputs/batch" --languages zh,en
python scripts/run.py build "example.pdf" --out "outputs/example" --resume --retry-pending
python scripts/run.py audit "outputs/example"
```

Unless another output location is specified, the agent uses `outputs/<PDF-filename-without-.pdf>/`, preserving the original name without translation or a generic replacement. For example, `example.pdf` produces `outputs/example/site/index.html`. The CLI still requires an explicit `--out` path.

`site/index.html` is the web entry, `extracted.txt` contains text, `manifest.json` is the per-page ledger, and `references/` holds local comparison images. Native text and vector graphics can be reused directly; scanned pages still require the agent to reconstruct regions, borders and ruby annotations. The script generates an editable draft; a successful conversion does not certify a faithful replica.

Supports passwords, mixed pages, varying sizes/rotations, table rules, isolated illustrations, form values, embedded PDF extraction, external OCR adapters, resume and batch error isolation. macOS can use built-in Vision; other systems can use Tesseract, external OCR or host vision tools.

## Validation

```sh
python scripts/selftest.py --out work/selftest
# Additional multilingual Vision check on macOS:
python scripts/selftest.py --out work/selftest-vision --vision
```

See the [validation record](references/validation.md), [main workflow](SKILL.md) and [agent integration](references/agents.md). The package contains no user PDFs, book content, source scans, extracted source fonts or private credentials.

## GitHub and version management

Source: <https://github.com/harisucici/pdf-web-replica>. The repository is public and can be cloned directly.

First installation from GitHub, using Hermes as an example:

```sh
git clone https://github.com/harisucici/pdf-web-replica.git
cd pdf-web-replica
python3 scripts/install.py --agent hermes
```

To update an existing installation, enter the local repository, pull the code and update the installed copy:

```sh
cd /path/to/pdf-web-replica
git pull --ff-only
python3 scripts/install.py --agent hermes --update
```

Replace `/path/to/pdf-web-replica` with your repository path. Replace `hermes` with `codex`, `opencode` or `openclaw` for other agents. Run the corresponding command separately for each agent you use.

`--update` backs up the old installation before replacing the skill files. The repository and installed skill are separate copies: **`git pull` alone does not update the installed skill**. Run the command with `--update`, then start a new agent session. This does not change agent settings, models or permissions.

The version is in `SKILL.md` under `metadata.version`. For a release, update [CHANGELOG.md](CHANGELOG.md), run checks and create the matching `vX.Y.Z` tag. Packaging includes only skill files, excluding Git history, test artifacts and PDFs:

```sh
python3 scripts/package.py --out dist
```

GitHub Actions runs synthetic PDF checks on Windows, macOS and Linux, with an additional Vision check on macOS. Passing automated checks does not establish page-by-page layout acceptance for an arbitrary document.

The source-quality route uses enhanced local OCR, separates body/ruby, matches serif/sans glyphs and crops artwork from the original PDF. See the [scan reconstruction procedure](references/scan-quality.md).

```sh
python3 scripts/bootstrap.py --venv work/.pdf-web-env --enhanced-ocr
# Use the returned Python interpreter:
<python> scripts/run.py build "book.pdf" --out "outputs/book" --languages ja,zh,ko,en --ocr rapidocr
<python> scripts/run.py enhance "outputs/book" --refine-ruby
```
