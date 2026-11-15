# ページと OCR のデータ形式

[中文](../../zh/references/page-schema.md) | [English](../../../references/page-schema.md) | [日本語](page-schema.md)

`<output>/manifest.json` は原本ハッシュ、総ページ数、処理範囲、全ページの状態を記録します。編集可能なファイルは `<output>/pages/00001.json` にあります。`site/pages/*.js` は生成物なので、JSON を編集して `refresh` を実行します。

## OCR の取り込み

```json
{
  "coordinate_space": "normalized",
  "blocks": [
    {
      "text": "Exact source text 한국어 日本語 中文",
      "bbox": [0.12, 0.18, 0.84, 0.21],
      "language": "ko",
      "confidence": 0.94
    }
  ]
}
```

境界は `[左, 上, 右, 下]` で、原点は左上です。`normalized` は 0–1、`pixels` は OCR 画像の `width` と `height` も必要、`pdf` は表示ページのポイント座標を使います。すべて**回転・クロップ後の描画ページ**を基準とし、未クロップの PDF media box ではありません。取り込みはそのページの文字ブロックを置換して確認フラグを消します。混在ページで元の文字やフォームを保持する場合は明示的に残します。

`blocks` は `text`、`bbox`、`origin`（基線）、`font_size`、`font_family`、`font_file`、`advance`、`angle`、`color`、`bold`、`italic`、`language`、`rtl`、`source`、`role` に対応します。ネイティブのフォームは項目名と型を保持し、チェックボックスとラジオボタンの状態は図形で描画します。複雑なフォームは別途検証が必要です。

`shapes` は独立した SVG 描画要素で、`path`、`fill`、`stroke`、`width`、`fill_opacity`、`stroke_opacity`、`even_odd` を持ちます。長方形は `M 40 50 H 220 V 120 H 40 Z` と表せます。原本の文字輪郭をトレースしたパスで本物の文字を置き換えません。

`images` は `site/` からの相対 `file` と、`bbox` または単位正方形をページへ写す六数値のアフィン `matrix` を持ちます。独立した図、ロゴ、写真にだけ使い、ページ全体や文字段落には使いません。ネイティブ抽出では内容ハッシュ付きの素材名を使います。

状態は `blank` が真の白紙、`needs_ocr` が未解決の文字、`error` が処理失敗、`draft` がデータはあるが原本確認未完了です。確認フラグ `text`、`layout`、`fonts`、`languages` は false から始まります。CLI で実際の検証を記録し、意味のある注記を添えます。

## 再開と公開

原本ハッシュで別の PDF に出力先を誤用することを防ぎます。書き込みはアトミックで、一部ページの失敗が成功済みページを消しません。公開するのは `site/` のみです。`references/`、作業用 OCR、原本 PDF は含めません。原本比較が求められた場合は、明示的な別モードとして追加し、通常ページの背景にはしません。

## 図版の承認

新しく抽出した `images` は `role: "illustration_candidate"`、`reviewed: false` です。独立した図版だけを含むと確認してから `role: "illustration"`、`reviewed: true` にします。承認済み項目だけがビューアーの幾何チェック対象を通過できます。これらの項目がない旧データは表示しません。bbox と行列の両方を調べ、不整合なメタデータで大画像の占有範囲を小さく偽れないようにします。ページスキャン、大きな疑似背景、合計でページを覆うタイルは通常の図版ではありません。参考にとどめ、文字と配置を再構築します。

`excluded_images` は旧画像の記述と `exclusion_reason` を残す診断データで、描画されません。更新したページは四つの確認フラグをリセットしますが、文字と手作業の注記は保持します。再構築と照合を終えたら通常の確認手順で合格を記録できます。除外履歴だけで再構築完了とは判断しません。

## ネイティブ HTML/CSS レイアウト

手作業で再構築したページでは `web_layout` を汎用 SVG 文字ブロックの代わりに表示できます。`elements` は独立した `div`、`span`、`svg`、`path` で、`style`（CSS 宣言）、`text`、`attrs`、`children` を持ちます。SVG 属性は `viewBox`、`d`、`fill`、`stroke`、`stroke-width`、`stroke-linejoin`、`aria-hidden` のみです。生 HTML、スクリプト、CSS URL 素材は非対応です。絶対配置は表示ページのポイント座標を使います。画像は `{ "tag": "img", "image_file": "illustrations/mascot.png" }` とし、同じファイルが `images` に承認済みで存在する必要があります。配置は承認済み bbox に従い、ノードの任意スタイルでは変更しません。

`web_layout.blocks` は `text`、正規化した `x`、`y`、`w`、`h`、ポイント単位の `size`、`font`（`serif`、`sans`、`korean`）、`bold`、`color` を使います。任意の `parts` は `text`、`bold`、`underline`、`rubies` は `text`、`offset`、`length` を持ちます。`number`、`numberSize`、`numberFont` で番号バッジを作れます。文字幅を測り、指定幅へ横方向に調整します。実際に表示・選択できる HTML span です。抽出・検索・監査用の対応する `blocks` / `text` も維持してください。`web_layout` の存在は忠実性や合格の証明ではありません。

任意の `reference_image` は、納品が許可された比較用原本画像を `site/` からの相対パスで指定します。比較ボタンを押した後だけ表示し、通常ページにしません。原画像を同梱する予定がなければ指定しないでください。`manifest.json` の `display_title`、`subtitle` でヘッダーを指定できます。既定 UI は従来の二段ツール領域、全文検索、文字サイドバー、幅調整です。PDF 固有の色、区画、書体は原本に基づいて再構築し、汎用テーマで代用しません。

## 原本に結び付く証拠とパッチ

`background_color` は原ページの地色です。`render_fingerprint` は `refresh` が生成し、捏造しません。表示データ、抽出文字、フォント・図版、ビューアーテンプレートをハッシュします。`review_signatures` は各確認をその版に結び付け、真偽フラグだけでは不足します。`layout_needs_sync` は OCR/文字の更新が残した手動レイアウトに未反映であることを示します。一致した `apply-layout` で解決し、旧表示を隠すためフラグだけ消しません。

`apply-layout` は `blocks`、`text`、`shapes`、`images`、`web_layout`、`background_color`、`reference_image` のみを受け、確認をリセットします。省略項目は保持し、`web_layout: null` は手動表示層を明示的に除きます。blocks 変更時に text がなければブロックから再生成します。撮影記録、比較、現行証拠の要件は[反復手順](fidelity.md)を参照してください。

`remaining_differences` は未解決の原本差異を示す空でない記述のリストです。配置パッチで更新でき、残項目は確認・監査の合格を止めます。診断用で、表示文字層ではありません。
