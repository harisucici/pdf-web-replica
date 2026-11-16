# PDF Web Replica

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

可移植的 PDF 文字提取、OCR、网页复刻技能。支持 Hermes Agent、Codex、OpenCode、OpenClaw，以及能读取 Agent Skills 格式的其他 Agent。

## 安装

解压后进入 `pdf-web-replica` 文件夹，选择对应 Agent：

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

Windows 可使用 `py -3` 代替 `python3`。已存在同名技能时，`--update` 会保留旧版本备份。不同 Hermes profile 或远程后端可用 `--root "实际技能目录"` 指定位置。安装只复制技能文件，不修改 Agent 设置、模型、权限或安全配置。

如需在整个 Hermes 会话中预加载技能，可启动：

```sh
hermes -s pdf-web-replica
```

## 客户端快速使用

安装后在 Hermes 客户端新建会话，附上 PDF，然后只需输入：

```text
/pdf-web-replica
```

也可以直接带上文件路径（路径有空格时加引号）：

```text
/pdf-web-replica "/path/to/example.pdf"
```

无需重复描述排版要求。默认提取全部文字，以可选择的网页文字复现原 PDF 的排版、样式和背景色，处理全部页面并逐页对照；不使用整页扫描图作为默认背景。输出目录为 `outputs/<PDF原文件名去掉.pdf>/`。文件未提供或存在多个候选时，Agent 会请你指定要处理的 PDF。尚未校验的内容会保留为待校对状态，不宣称完整复刻已通过。

安装必须位于实际运行 Hermes 的机器、profile 或远程后端中，PDF 也必须能被该环境访问。只安装在本机不会自动同步到远程服务器。

其他 Agent 可直接要求“使用 pdf-web-replica 处理这个 PDF”，并附上文件或路径。各宿主的加载方式见 [Agent 集成说明](docs/zh/references/agents.md)。Hermes 的简短调用方式依据[官方技能文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)。

Hermes 的技能入口不设操作系统、工具集、API key 或 PDF 类型准入限制。读取到扫描页时会继续选择 OCR 或配置好的视觉工具，不会因为“这是 PDF”就直接拒绝。但任何软件都不能保证损坏文件、未知密码或不可用工具环境下必然成功；这些情况会输出具体诊断，不伪造完成。

## 按原 PDF 重建与验收

默认目标是尽可能忠实复现原页，而不是提取完 OCR 就结束。文档内部的颜色、分区、字体、间距、注音、表格和插图必须来自原 PDF；通用阅读器界面不能替代原页排版。原文中的错字也不擅自改写。

初稿之后还需运行版式分析、按原件重建、浏览器逐页截图、差异修正和最终审计：

```sh
python scripts/run.py analyze "outputs/example"
python scripts/run.py apply-layout "outputs/example" --page 1 --json "work/page-1-layout.json"
python scripts/run.py refresh "outputs/example"
python scripts/run.py compare "outputs/example" --captures "work/browser-captures"
python scripts/run.py audit "outputs/example"
```

`analyze` 给出原件总览、色块/线条候选、版式分组和逐页任务；候选必须核对后再采用。`compare` 使用真实默认网页截图，输出并排、叠加、差异图和待修正区域。没有当前视觉证据或仍有明显差异时，不能把排版/字体标记通过；页面、字体、插图或查看器修改后旧验收失效。所有页面均需对照，像素指标不等于“还原率”，不能掩盖细小错字。

截图方法、元数据、修正流程及验收命令见[忠实复刻迭代流程](docs/zh/references/fidelity.md)。核心分析/对比依赖 PyMuPDF、Pillow，无需独立 OCR skill；实际 OCR 与浏览器能力由运行环境提供。脚本是辅助工具，Agent 必须继续做原页重建，不能承诺任何文件都无条件达到 100%。

## 本地命令

```sh
python3 scripts/run.py doctor
python3 scripts/bootstrap.py --venv work/.pdf-web-env
```

如果需要隔离环境，后续使用 bootstrap 返回的 Python 路径：

```sh
python scripts/run.py build "example.pdf" --out "outputs/example" --languages ja,zh,ko,en
python scripts/run.py batch "pdf-folder" --out "outputs/batch" --languages zh,en
python scripts/run.py build "example.pdf" --out "outputs/example" --resume --retry-pending
python scripts/run.py audit "outputs/example"
```

未指定其他输出位置时，Agent 使用 `outputs/<PDF文件名（去掉 .pdf）>/`，目录保留原文件名，不翻译或替换成固定名称。例如 `example.pdf` 对应 `outputs/example/site/index.html`。CLI 仍需通过 `--out` 显式传入输出路径。

`site/index.html` 为网页，`extracted.txt` 为文字，`manifest.json` 为逐页记录，`references/` 为本地对照图。网页文字和原生矢量图形可直接复用；扫描页必须继续由 Agent 重建分区、框线、注音等元素。脚本生成的是可继续校对的底稿，不能把“一次转换成功”当成“完全复刻通过”。

支持密码参数、混合页面、不同页面尺寸/旋转、表格线、独立插图、表单值、内嵌 PDF 提取、外部 OCR 适配、断点续跑和批量错误隔离。macOS 可用内置 Vision；其他系统可使用 Tesseract 或外部 OCR/宿主视觉工具。

## 验证

```sh
python scripts/selftest.py --out work/selftest
# macOS 另测多语言 Vision：
python scripts/selftest.py --out work/selftest-vision --vision
```

验证记录见 [references/validation.md](docs/zh/references/validation.md)。中文流程见 [工作流程](docs/zh/workflow.md)，正式加载入口为 [SKILL.md](SKILL.md)，平台差异见 [references/agents.md](docs/zh/references/agents.md)。此技能包不包含任何用户的 PDF、书籍内容、源扫描页、提取字体或私人凭据。

## GitHub 与版本管理

源码仓库：<https://github.com/harisucici/pdf-web-replica>。当前为公开仓库，可直接克隆。

首次从 GitHub 安装（以 Hermes 为例）：

```sh
git clone https://github.com/harisucici/pdf-web-replica.git
cd pdf-web-replica
python3 scripts/install.py --agent hermes
```

更新已有安装时，先进入本地仓库目录，再拉取代码并更新技能副本：

```sh
cd /path/to/pdf-web-replica
git pull --ff-only
python3 scripts/install.py --agent hermes --update
```

将 `/path/to/pdf-web-replica` 替换为实际仓库路径。其他 Agent 将 `hermes` 替换为 `codex`、`opencode` 或 `openclaw`；安装到多个 Agent 时，分别执行对应的安装或更新命令。

`--update` 会备份已安装的旧版本，然后替换技能文件。仓库源码与 Agent 已安装的技能是独立副本，**仅执行 `git pull` 不会更新已安装的技能**，还需执行上述带 `--update` 的命令。更新后开启新的 Agent 会话加载新版。此过程不修改 Agent 设置、模型或权限。

版本号位于 `SKILL.md` 的 `metadata.version`。发布新版本时，同步更新 [更新记录](docs/zh/CHANGELOG.md)、运行检查，再建立对应的 `vX.Y.Z` 标签。打包命令只收录技能文件，不会收录 Git 历史、测试产物或 PDF：

```sh
python3 scripts/package.py --out dist
```

GitHub Actions 会在 Windows、macOS、Linux 上运行合成 PDF 测试；macOS 额外检查 Vision OCR。自动检查通过不代表任意输入文档的版式已经完成逐页验收。

新版默认质量基线：使用增强本地 OCR，分离正文/注音，匹配明朝与黑体，图标从原 PDF 裁切。详见[扫描件复刻流程](docs/zh/references/scan-quality.md)。

```sh
python3 scripts/bootstrap.py --venv work/.pdf-web-env --enhanced-ocr
# Use the returned Python interpreter:
<python> scripts/run.py build "book.pdf" --out "outputs/book" --languages ja,zh,ko,en --ocr rapidocr
<python> scripts/run.py enhance "outputs/book" --refine-ruby
```
