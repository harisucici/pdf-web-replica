# PDF Web Replica

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

也可以在 Hermes 新会话中直接发送：

```text
/pdf-web-replica 处理这个 PDF：提取全部文字，并用真正可选择的网页文字完整还原排版。不要使用整页图片或扫描底图，处理全部页，逐页对照验收。
```

Hermes 的技能入口不设操作系统、工具集、API key 或 PDF 类型准入限制。读取到扫描页时会继续选择 OCR 或配置好的视觉工具，不会因为“这是 PDF”就直接拒绝。但任何软件都不能保证损坏文件、未知密码或不可用工具环境下必然成功；这些情况会输出具体诊断，不伪造完成。

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
python scripts/selftest.py --out work/独立测试目录
# macOS 另测多语言 Vision：
python scripts/selftest.py --out work/独立视觉测试目录 --vision
```

验证记录见 [references/validation.md](references/validation.md)。主流程见 [SKILL.md](SKILL.md)，平台差异见 [references/agents.md](references/agents.md)。此技能包不包含任何用户的 PDF、书籍内容、源扫描页、提取字体或私人凭据。

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

版本号位于 `SKILL.md` 的 `metadata.version`。发布新版本时，同步更新 `CHANGELOG.md`、运行检查，再建立对应的 `vX.Y.Z` 标签。打包命令只收录技能文件，不会收录 Git 历史、测试产物或 PDF：

```sh
python3 scripts/package.py --out dist
```

GitHub Actions 会在 Windows、macOS、Linux 上运行合成 PDF 测试；macOS 额外检查 Vision OCR。自动检查通过不代表任意输入文档的版式已经完成逐页验收。
