# Agent 集成

[中文](agents.md) | [English](../../../references/agents.md) | [日本語](../../ja/references/agents.md)

本包是 Agent Skills 文件夹，不是 Codex 专用插件。必须复制包含脚本和资源的**完整**文件夹，在 Agent 实际运行环境执行 Python 命令。安装器不修改设置、沙箱、权限、允许列表或模型配置。

| Agent | 用户技能位置 | 显式调用 |
|---|---|---|
| Hermes Agent | `~/.hermes/skills/pdf-web-replica/` | `/pdf-web-replica [PDF路径]` |
| Codex | `$CODEX_HOME/skills/pdf-web-replica/`；默认根目录 `~/.codex/skills/` | `$pdf-web-replica` |
| OpenCode | `$XDG_CONFIG_HOME/opencode/skills/pdf-web-replica/`；默认根目录 `~/.config/opencode/skills/` | 要求使用 `pdf-web-replica`，由 Agent 的 `skill` 工具加载 |
| OpenClaw | `~/.openclaw/skills/pdf-web-replica/` | 提及技能名或用宿主的技能选择器 |
| 其他 Agent Skills 宿主 | 宿主支持的技能根目录 | 加载 `SKILL.md`，按相对位置读取资源 |

从解压后的包根目录执行：

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

`--root <skill-root>` 显式选择 profile 或项目目录；`--dry-run` 仅显示路径；`--update` 先创建时间戳备份再替换现有技能。技能目录被缓存时，开启新会话。

## 客户端最简使用

Hermes 新会话附上 PDF，输入 `/pdf-web-replica`；也可以发送 `/pdf-web-replica "/path/to/example.pdf"`。无需重复排版要求，默认进行全文、全页的可选文字重建和原件对照。没有可访问的 PDF 时提供路径或附件，候选多个时指定其中一个。必须安装在实际执行的机器、profile、后端中。快捷命令未出现可能是会话缓存、profile 不同或安装到了错误后端；开启新会话并检查安装位置。OpenCode 使用技能加载工具，不假定通用的 `@技能名` 快捷语法。

## 优先支持 Hermes

本技能不设置 `platforms`、`required_environment_variables`、`requires_tools`、`requires_toolsets` 或回退准入条件，因此不在包层面限制 OS、API key 或工具集。用户主动禁用技能的设置仍优先。不同 profile 有独立目录，应安装到所选 profile，或正确使用 `HERMES_HOME` / `--root`。

通过 Hermes 的 `terminal` 运行命令。Agent 使用不同 Python 时优先执行 `python scripts/run.py ...`，分发器会寻找可用的 PDF 解释器或提示隔离环境安装步骤。远程或容器后端中，技能和 PDF 必须在**后端内部**可见；宿主路径不会自动变成容器路径。在后端内建立 Python 环境。Linux/Windows 使用 Tesseract、外部 OCR 或已配置的视觉工具；macOS Vision 是可选能力，不是技能发现条件。

Hermes 的 `read_file` 能提取文档文字，但可能提示扫描部分不可读。全文重建任务中，这些缺失必须继续处理，不能借此只抽样或跳页。已配置的 `vision_analyze` 可读取渲染页，应使用实际发现的接口。可用的 `ocr-and-documents` 技能可协助批量 OCR，但不是依赖。按页面格式导入带坐标的结果，不编造 `document_extract` 工具，也不假设某个视觉服务已配置。

## 其他宿主

Codex 通过终端运行 CLI。`agents/openai.yaml` 是可选 UI 元数据，其他宿主可忽略。OpenCode 与 OpenClaw 使用同一 `SKILL.md`，主流程不绑定框架专有工具名。OpenClaw 也可使用其本地文件夹安装器。遵守宿主对可信技能来源的要求，本包不绕过它们。

## 已核对的官方资料

核对日期：2026-11-15。宿主发现机制改变时重新核对。

- [Hermes 技能格式与条件加载](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
- [Hermes 技能目录与调用](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes 文档提取与扫描缺失](https://hermes-agent.nousresearch.com/docs/user-guide/features/document-extraction)
- [OpenCode 技能](https://opencode.ai/docs/skills/)
- [OpenClaw 技能](https://docs.openclaw.ai/tools/skills)
