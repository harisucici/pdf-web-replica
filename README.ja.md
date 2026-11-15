# PDF Web Replica

[中文](README.md) | [English](README.en.md) | [日本語](README.ja.md)

PDF の文字抽出、OCR、Web ページへの再構築を行う移植可能なスキルです。Hermes Agent、Codex、OpenCode、OpenClaw、および Agent Skills 形式を読み込めるホストに対応します。

## インストール

パッケージを展開して `pdf-web-replica` フォルダーに移動し、使用する Agent を選びます。

```sh
python3 scripts/install.py --agent hermes
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent opencode
python3 scripts/install.py --agent openclaw
```

Windows では必要に応じて `python3` の代わりに `py -3` を使います。同名スキルがある場合、`--update` は旧版をバックアップします。別の Hermes プロファイルやバックエンドには `--root "/path/to/skills"` でインストール先を指定できます。ファイルのコピーのみを行い、Agent の設定、モデル、権限、セキュリティ設定は変更しません。

Hermes のセッション開始時に読み込む場合：

```sh
hermes -s pdf-web-replica
```

## クライアントで簡単に使う

インストール後、Hermes で新しい会話を開き、PDF を添付して次のコマンドだけを送ります。

```text
/pdf-web-replica
```

ファイルパスを直接指定することもできます。空白を含むパスは引用符で囲みます。

```text
/pdf-web-replica "/path/to/example.pdf"
```

毎回レイアウトの要件を説明する必要はありません。既定では全文を抽出し、選択可能な Web テキストで元のレイアウト、スタイル、背景色を再現し、全ページを処理して原本と照合します。ページ全体のスキャン画像を通常の背景には使いません。出力先は `outputs/<元のPDFファイル名から.pdfを除いた名前>/` です。PDF が未指定、または候補が複数ある場合は、対象ファイルを確認します。未検証の内容は校正待ちの下書きとして残し、完全再現済みとは表示しません。

Hermes が実際に動作するマシン、プロファイル、リモートバックエンドにインストールしてください。PDF もその環境からアクセスできる必要があります。ローカルのインストールはリモートサーバーへ自動同期されません。

他の Agent では「pdf-web-replica を使ってこの PDF を処理して」と依頼し、ファイルまたはパスを渡します。ホストごとの読み込み方法は [Agent 連携](docs/ja/references/agents.md) を参照してください。Hermes の簡単な呼び出し方は[公式スキル文書](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)に基づきます。

Hermes での読み込み時に OS、ツールセット、API キー、PDF の種類による制限は設けていません。スキャンには OCR や設定済みの画像認識ツールを使います。ただし、破損ファイル、不明なパスワード、利用できない実行環境での成功を保証することはできません。その場合は具体的な診断を示し、完了を装いません。

## 原 PDF に基づく再構築と確認

既定の目標は原本に可能な限り近づけることで、OCR 終了では止めません。文書内の色、区画、書体、間隔、ルビ、表、図版は実際の PDF に基づけます。汎用の読書 UI は原ページの配置を代替しません。原文の誤字も勝手に書き換えません。

初稿の後も原本分析、再構築、実ブラウザー撮影、差分修正、監査を続けます。

```sh
python scripts/run.py analyze "outputs/example"
python scripts/run.py apply-layout "outputs/example" --page 1 --json "work/page-1-layout.json"
python scripts/run.py refresh "outputs/example"
python scripts/run.py compare "outputs/example" --captures "work/browser-captures"
python scripts/run.py audit "outputs/example"
```

`analyze` は一覧、色・線の候補、レイアウト分類、ページ作業を示します。候補は確認してから採用します。`compare` は実際の通常 Web 表示を使い、並列・重ね合わせ・差分・最大差異領域を生成します。現行の視覚証拠がない場合や大きな差異が残る場合、配置・フォントを合格にできません。ページ、フォント、図版、ビューアーの変更で旧確認は失効します。全ページを照合し、指標を「再現率」と呼んだり、小さな誤字を見逃したりしません。

撮影記録、反復、確認コマンドは[忠実性の反復手順](docs/ja/references/fidelity.md)を参照してください。分析・比較は PyMuPDF と Pillow を使い、別の OCR スキルは不要です。実 OCR とブラウザー能力は実行環境が提供します。スクリプトは補助であり、Agent が原本の再構築を続けます。あらゆるファイルの無条件 100% 成功は保証しません。

## ローカルコマンド

```sh
python3 scripts/run.py doctor
python3 scripts/bootstrap.py --venv work/.pdf-web-env
```

隔離環境が必要な場合は、bootstrap が返す Python インタープリターを使います。

```sh
python scripts/run.py build "example.pdf" --out "outputs/example" --languages ja,zh,ko,en
python scripts/run.py batch "pdf-folder" --out "outputs/batch" --languages zh,en
python scripts/run.py build "example.pdf" --out "outputs/example" --resume --retry-pending
python scripts/run.py audit "outputs/example"
```

別の出力先が指定されていない場合、Agent は `outputs/<PDFファイル名から.pdfを除いた名前>/` を使用します。原名を保ち、翻訳や固定名への置き換えはしません。例：`example.pdf` → `outputs/example/site/index.html`。CLI では引き続き `--out` に明示的なパスが必要です。

`site/index.html` が Web の入口、`extracted.txt` が抽出テキスト、`manifest.json` がページ別の記録、`references/` がローカル比較画像です。元の文字やベクター図形は再利用できますが、スキャンでは領域、枠線、ふりがななどの再構築が必要です。スクリプトの出力は校正可能な下書きであり、変換成功だけで完全再現の合格にはなりません。

パスワード、混在ページ、異なるサイズや回転、表の罫線、独立したイラスト、フォーム値、埋め込み PDF の抽出、外部 OCR、再開、バッチ内のエラー分離に対応します。macOS では内蔵 Vision、他の環境では Tesseract、外部 OCR、ホストの画像認識ツールが利用できます。

## 検証

```sh
python scripts/selftest.py --out work/selftest
# macOS では多言語 Vision も確認：
python scripts/selftest.py --out work/selftest-vision --vision
```

[検証記録](docs/ja/references/validation.md)、[メインの手順](docs/ja/workflow.md)、[Agent 連携](docs/ja/references/agents.md)を参照してください。このパッケージに利用者の PDF、書籍本文、原本スキャン、抽出した原本フォント、個人の認証情報は含まれません。

## GitHub とバージョン管理

ソース：<https://github.com/harisucici/pdf-web-replica>。公開リポジトリなので直接クローンできます。

GitHub から初めてインストールする場合（Hermes の例）：

```sh
git clone https://github.com/harisucici/pdf-web-replica.git
cd pdf-web-replica
python3 scripts/install.py --agent hermes
```

更新時はローカルリポジトリに移動し、コードを取得してインストール済みのコピーを更新します。

```sh
cd /path/to/pdf-web-replica
git pull --ff-only
python3 scripts/install.py --agent hermes --update
```

`/path/to/pdf-web-replica` は実際のリポジトリパスに置き換えます。他の Agent では `hermes` を `codex`、`opencode`、`openclaw` に変更します。複数の Agent にインストールする場合は、それぞれ実行してください。

`--update` は旧版をバックアップしてからスキルファイルを置き換えます。リポジトリとインストール済みスキルは別コピーなので、**`git pull` だけではインストール済みスキルは更新されません**。`--update` 付きのコマンドを実行し、新しい Agent セッションを開いてください。Agent の設定、モデル、権限は変更しません。

バージョン番号は `SKILL.md` の `metadata.version` にあります。リリース時は [変更履歴](docs/ja/CHANGELOG.md)を更新し、検証後に対応する `vX.Y.Z` タグを作成します。パッケージにはスキル関連ファイルのみが入り、Git 履歴、テスト生成物、PDF は含まれません。

```sh
python3 scripts/package.py --out dist
```

GitHub Actions は Windows、macOS、Linux で合成 PDF のテストを行い、macOS では Vision も確認します。自動テストに合格しても、任意の PDF の全ページでレイアウト検証が完了したことにはなりません。
