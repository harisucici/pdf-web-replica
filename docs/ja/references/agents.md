# Agent 連携

[中文](../../zh/references/agents.md) | [English](../../../references/agents.md) | [日本語](agents.md)

このパッケージは Agent Skills フォルダーであり、Codex 専用プラグインではありません。スクリプトと素材を含む**フォルダー全体**をコピーし、Agent の実際の実行環境で Python コマンドを実行します。インストーラーは設定、サンドボックス、権限、許可リスト、モデル構成を変更しません。

| Agent | ユーザースキルの場所 | 明示的な呼び出し |
|---|---|---|
| Hermes Agent | `~/.hermes/skills/pdf-web-replica/` | `/pdf-web-replica [PDFパス]` |
| Codex | `$CODEX_HOME/skills/pdf-web-replica/`。既定のルートは `~/.codex/skills/` | `$pdf-web-replica` |
| OpenCode | `$XDG_CONFIG_HOME/opencode/skills/pdf-web-replica/`。既定のルートは `~/.config/opencode/skills/` | `pdf-web-replica` の使用を依頼し、Agent が `skill` ツールで読み込む |
| OpenClaw | `~/.openclaw/skills/pdf-web-replica/` | スキル名を伝えるか、ホストの選択機能を使う |
| その他の Agent Skills ホスト | 対応するスキルルート | `SKILL.md` を読み、相対パスのファイルを解決する |

展開したパッケージのルートで実行します。

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

`--root <skill-root>` はプロファイルやプロジェクトを明示指定します。`--dry-run` は変更せずパスだけを表示し、`--update` は日時付きバックアップを作ってから置き換えます。スキル一覧がキャッシュされている場合は新しいセッションを開きます。

## クライアントでの最小操作

Hermes の新しい会話に PDF を添付して `/pdf-web-replica` を送ります。`/pdf-web-replica "/path/to/example.pdf"` でも構いません。レイアウト要件を繰り返す必要はなく、全文・全ページを選択可能な文字として再構築し原本と比較します。利用可能な PDF がなければパスか添付を渡し、複数候補がある場合は対象を指定します。実行するマシン、プロファイル、バックエンドにインストールしてください。コマンドが出ない場合はキャッシュ、別プロファイル、別バックエンドへのインストールを確認し、新しい会話を開きます。OpenCode はスキル読み込みツールを使い、汎用の `@スキル名` 構文は前提にしません。

## Hermes を優先

このスキルには `platforms`、`required_environment_variables`、`requires_tools`、`requires_toolsets` やフォールバックの読み込み条件を設けていません。パッケージ側に OS、API キー、ツールセットの資格制限はありません。ただし利用者が明示的に無効化した設定には従います。プロファイルごとにホームが異なるため、選択中のスキルディレクトリへインストールするか `HERMES_HOME` / `--root` を正しく指定します。

Hermes の `terminal` から実行します。異なる Python 環境では `python scripts/run.py ...` を優先し、ディスパッチャーが対応するインタープリターを探すか、隔離環境の作成手順を返します。リモートやコンテナーではスキルと PDF が**そのバックエンド内**から見える必要があります。ホストのパスは自動変換されません。その環境に Python を用意します。Linux/Windows では Tesseract、外部 OCR、設定済みの画像認識を利用します。macOS Vision は任意で、スキル検出の条件ではありません。

Hermes の `read_file` は文書を抽出できますが、スキャンの読めない部分を警告することがあります。全文再構築の依頼では、その欠落を補完し、一部抽出やページ省略の許可とは解釈しません。設定済みの `vision_analyze` はレンダリング画像を読めます。実際に検出したインターフェースを使ってください。利用できる `ocr-and-documents` スキルは補助にできますが依存ではありません。座標付き結果をページ形式で取り込み、`document_extract` というツールを捏造したり、特定の画像認識プロバイダーがあると決めつけたりしません。

## その他のホスト

Codex はターミナルから CLI を実行できます。`agents/openai.yaml` は任意の UI メタデータで、他ホストでは無視されます。OpenCode と OpenClaw は同じ `SKILL.md` を使い、主手順にフレームワーク専用ツール名を持ち込みません。OpenClaw のローカルフォルダー用インストーラーも利用できます。ホストの信頼済みソースに関する規則に従い、回避しません。

## 確認した公式資料

確認日：2026-11-15。ホストの検出方法が変わった場合は再確認してください。

- [Hermes のスキル形式と条件付き読み込み](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
- [Hermes のスキル場所と呼び出し](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes の文書抽出とスキャンの欠落](https://hermes-agent.nousresearch.com/docs/user-guide/features/document-extraction)
- [OpenCode のスキル](https://opencode.ai/docs/skills/)
- [OpenClaw のスキル](https://docs.openclaw.ai/tools/skills)
