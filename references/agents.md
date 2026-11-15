# Agent integration

[中文](../docs/zh/references/agents.md) | [English](agents.md) | [日本語](../docs/ja/references/agents.md)

This package is an Agent Skills folder, not a Codex-only plugin. Copy the **entire** folder, including scripts and assets. Run its Python commands in the agent's actual execution environment. No agent setting, sandbox, permission, allowlist, or model configuration is changed by the installer.

| Agent | User skill location | Explicit invocation |
|---|---|---|
| Hermes Agent | `~/.hermes/skills/pdf-web-replica/` | `/pdf-web-replica [PDF path]` |
| Codex | `$CODEX_HOME/skills/pdf-web-replica/`, default `~/.codex/skills/` | `$pdf-web-replica` |
| OpenCode | `$XDG_CONFIG_HOME/opencode/skills/pdf-web-replica/`, default `~/.config/opencode/skills/` | Ask to use `pdf-web-replica`; the agent loads its `skill` tool |
| OpenClaw | `~/.openclaw/skills/pdf-web-replica/` | Mention the skill or use the host's skill picker |
| Other Agent Skills hosts | Their supported skills root | Load `SKILL.md` and resolve its relative files |

From the unpacked package:

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

`--root <skill-root>` selects a profile or project explicitly. `--dry-run` prints paths without changes. `--update` keeps a timestamped backup before replacing an existing skill. Open a fresh agent session if its skill catalog is cached.

## Minimal client use

Attach a PDF in a new Hermes conversation and send `/pdf-web-replica`. Alternatively send `/pdf-web-replica "/path/to/example.pdf"`. No repeated layout instructions are needed: the skill defaults to full-document selectable-text reconstruction and source comparison. If no PDF is accessible, specify its path or attach it; if several are ambiguous, identify one. Install in the actual execution machine/profile/backend, not just the desktop host. A missing slash-command listing can indicate a cached session, a different profile, or an installation in the wrong backend. Start a fresh session and verify the installation location. OpenCode uses its skill-loading tool; a universal `@skill-name` shortcut is not assumed.

## Hermes first

The skill deliberately omits `platforms`, `required_environment_variables`, `requires_tools`, `requires_toolsets`, and fallback gates. Hermes therefore has no package-imposed OS, API-key or toolset eligibility restriction. A user's explicit disabled-skill setting still takes precedence. Different Hermes profiles have separate homes; install in the selected profile's skill directory, or use `HERMES_HOME`/`--root` appropriately.

Run commands through Hermes `terminal`. Prefer `python scripts/run.py ...` when its agent runtime uses a different Python: the dispatcher finds an available PDF interpreter, or reports the isolated bootstrap step. For a remote or container backend, ensure the skill folder and input PDF are visible **inside that backend**; host-only paths do not become container paths automatically. Bootstrap a local Python environment there. On Linux/Windows, use Tesseract, an external OCR adapter, or the host's configured vision route; the macOS Vision helper is optional, never a discovery requirement.

Hermes `read_file` can extract document text but may warn about unreadable scanned gaps. For a user's full-document reconstruction request, those gaps are work to complete, not permission to sample or omit pages. The configured `vision_analyze` tool can read rendered pages; use its actual discovered interface. An available `ocr-and-documents` skill can assist with bulk OCR but is not a dependency of this package. Import coordinate-bearing results through the page schema. Do not invent a tool named `document_extract` or assume a particular vision provider is configured.

## Other hosts

Codex can execute the CLI using its terminal capabilities. `agents/openai.yaml` is optional UI metadata, ignored by the other hosts. OpenCode and OpenClaw load the same `SKILL.md`; no framework-specific tool names appear in the main workflow. OpenClaw can also install a local folder using its own installer. Follow host policies for trusted skill sources; the package does not bypass them.

## Verified source references

Checked 2026-11-15. Re-check upstream docs when a host changes discovery behavior.

- [Hermes skill format and conditional loading](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
- [Hermes skill directories and invocation](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes document extraction and scanned gaps](https://hermes-agent.nousresearch.com/docs/user-guide/features/document-extraction)
- [OpenCode skills](https://opencode.ai/docs/skills/)
- [OpenClaw skills](https://docs.openclaw.ai/tools/skills)
