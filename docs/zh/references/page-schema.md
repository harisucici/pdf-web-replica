# 页面与 OCR 数据格式

[中文](page-schema.md) | [English](../../../references/page-schema.md) | [日本語](../../ja/references/page-schema.md)

`<output>/manifest.json` 记录源文件哈希、总页数、处理范围和每页状态。可编辑文件位于 `<output>/pages/00001.json`。`site/pages/*.js` 是生成物，应修改 JSON 后运行 `refresh`。

## OCR 导入

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

边界框为 `[左, 上, 右, 下]`，原点在左上角。`normalized` 使用 0–1；`pixels` 还需 OCR 图像的 `width` 和 `height`；`pdf` 使用显示页面坐标中的点。全部坐标以**旋转、裁切后的渲染页**为准，不是未经裁切的 PDF media box。导入 OCR 会替换该页文字块并清除校验标记。混合页需要保留原生或表单块时，应显式保留。

`blocks` 支持 `text`、`bbox`、`origin`（基线）、`font_size`、`font_family`、`font_file`、`advance`、`angle`、`color`、`bold`、`italic`、`language`、`rtl`、`source`、`role`。原生表单保留字段名和类型；复选框、单选框快照以形状显示。复杂表单仍需验证。

`shapes` 是独立 SVG 绘图元素，字段为 `path`、`fill`、`stroke`、`width`、`fill_opacity`、`stroke_opacity`、`even_odd`。矩形可表示为 `M 40 50 H 220 V 120 H 40 Z`。不得用源文字轮廓描摹路径替代真实文字。

`images` 包含相对于 `site/` 的 `file`，以及 `bbox` 或将单位正方形映射到页面的六数字仿射 `matrix`。仅用于独立插图、标志和照片，不能用于页面截图或文字段落。原生提取使用内容哈希命名资源。

状态：`blank` 为原件真空白；`needs_ocr` 为文字未解决；`error` 为处理失败；`draft` 为已有数据但未完成原件校验。`text`、`layout`、`fonts`、`languages` 校验标记初始为 false。通过 CLI 记录实际核对，并提供有意义的备注。

## 续跑与发布

源文件哈希防止将旧输出目录误用于另一份 PDF。写入具有原子性；单页失败不会丢弃其他成功页面。只发布 `site/`，其中不含 `references/`、OCR 工作文件或原 PDF。用户需要对照功能时，明确增加独立、标注清晰的比较模式，不能将原件作为正常页面背景。

## 插图确认

新提取的 `images` 使用 `role: "illustration_candidate"`、`reviewed: false`。核对资源确实只含独立插图后，设置 `role: "illustration"`、`reviewed: true`；只有确认后的图片才有资格通过查看器的几何检查。旧数据缺少字段时不显示。bbox 与矩阵都检查，不能用不一致的元数据缩小大图的实际占地。页面扫描、大幅疑似底图和合起来覆盖页面的拼接图均不能当正常插图；仅留作参考并重建文字、排版。

`excluded_images` 保存旧图片描述与 `exclusion_reason`，只用于诊断，不渲染。刷新对变更页重置四项校验标记，但保留文字和手工备注。实际重建并核对后，可按正常流程记录验收；排除历史本身不能证明已重建完成。

## 原生 HTML/CSS 排版

手工重建页可使用 `web_layout`，替代通用 SVG 文字块的显示。`elements` 包含独立的 `div`、`span`、`svg`、`path` 节点，字段为 `style`（CSS 声明）、`text`、`attrs`、`children`。SVG 属性仅支持 `viewBox`、`d`、`fill`、`stroke`、`stroke-width`、`stroke-linejoin`、`aria-hidden`。不支持原始 HTML、脚本或 CSS URL 资源。绝对定位以显示页面的点坐标为准。位图节点为 `{ "tag": "img", "image_file": "illustrations/mascot.png" }`，必须同时在 `images` 中存在已确认的记录；位置取该记录的 bbox，不能用节点样式任意改位置。

`web_layout.blocks` 支持 `text`、归一化 `x`、`y`、`w`、`h`、点单位字号 `size`、`font`（`serif`、`sans`、`korean`）、`bold`、`color`。可选 `parts` 包含 `text`、`bold`、`underline`；`rubies` 包含 `text`、`offset`、`length`；`number`、`numberSize`、`numberFont` 创建独立编号标记。查看器测量文字后横向缩放到指定宽度，仍为可见、可选择的 HTML span。页面记录中仍需维护对应 `blocks` / `text`，供提取、搜索、审计；存在 `web_layout` 不证明已忠实复刻或验收。

可选 `reference_image` 指定相对于 `site/` 的、已授权纳入交付的原件对照资源。只有点击对照按钮后才显示，不能作为正常页面。未计划交付原图时不设置此字段。`manifest.json` 可设 `display_title`、`subtitle` 作为阅读器标题。默认界面使用之前的双栏工具区、全文搜索、文字侧栏和宽度控制；PDF 自身的颜色、分区、字体仍需按原件重建，不能用通用主题代替。

## 原件绑定证据与排版补丁

`background_color` 指定原页底色。`render_fingerprint` 由 `refresh` 生成，不能编造，覆盖可见页面数据、提取文字、字体/插图文件和查看器模板。`review_signatures` 把各项完成记录绑定到该版本，只有布尔标记不够。`layout_needs_sync` 表示 OCR/文字更新尚未反映到保留的手工排版；用一致的 `apply-layout` 补丁解决，不能只清标记掩盖旧文字。

`apply-layout` 只接受 `blocks`、`text`、`shapes`、`images`、`web_layout`、`background_color`、`reference_image`，并重置校验。省略字段保留；`web_layout: null` 显式移除手工显示层。修改 blocks 但未给 text 时，按块重建全文。截图元数据、对比和当前证据要求见[迭代流程](fidelity.md)。

`remaining_differences` 是尚未解决的原件差异描述列表，每项不能为空。可用排版补丁更新；未解决项阻止验收和审计通过。它是诊断记录，不是页面文字层。
