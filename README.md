# booth-proposal

**展台方案的 AI 设计伙伴，面向展览设计公司。**

给它一份展台招标书和客户的参考照片，它会在几分钟内给出三个明显不同的展台方向的效果图；你选定之后，再补上尺寸核算、平面图和方案文字，最后生成一份可以直接发给客户的提案 PDF。

它是一个 [Agent Skill](https://agentskills.io)，同一个文件夹可在 Claude Code、Claude.ai、Codex、ChatGPT 和 GitHub Copilot 中使用。

## 一次完整的流程

| 步骤 | 做什么 | 产出 |
| --- | --- | --- |
| 1 简报 | 读标书和全部客户资料：每条要求标编号和出处，缺的信息做假设而不是提问，整理可用的客户原文，列出提案要回应的设计要点 | `brief/` 里的需求卡、场馆卡、内容清单、设计要点 |
| 2 框架 | 展位尺寸、限高、开口、功能项（大屏、展示、吧台、洽谈等）和面积、进深预算 | `brief/` 里的框架卡 |
| 3 想法 | 逐张看参考图，记下客户喜欢的地方（结构、颜色、光、完成度）；洞察要写明出自标书或客户资料，或者明说是我们的看法；写五六个一句话想法，选三个明显不同的。方案可以从参考图演化，但至少一个从别处出发（品牌故事、内容或某个设计方向） | 三个方向 |
| 4 出图 | 每个方向写一段短提示词，**连同参考照片本身**一起交给图像模型，各出 2 张候选；选一张，以画面里的人为比例尺目测尺寸，小问题修图，尺寸明显不对就重出；再由选定的图编辑出正面视图 | 每个方案一张主视图、一张正面视图 |
| 5 深化 | 按选定的效果图写几何数据并核算，画平面图，做附录用的白模，写方案文字和墙面内容 | 平面图、方案文字、核算结果 |
| 6 提案 | `deck.py` 生成提案，补全文字，`check` 通过后 `render` 导出 PDF。提案只展示设计，附录最多 3 页 | `pack/proposal.pdf` |

第 1、2 步只记录项目事实，放在 `brief/` 里，以后重做方案时直接复用。第 3 步选定三个方向后马上进入第 4 步，所以几分钟内就能先看到图。

整个过程不会停下来问你缺什么信息：先做合理假设并标明，之后随时可以改（例如 `change A1: 三面开口`），只重做受影响的部分。

## 参考图只是输入

参考照片（客户上一版的方案、客户喜欢的图、标书里的插图）是设计的输入：出图时发给图像模型，也给设计师看，方案可以从中演化。

但提案展示的是我们自己的设计：

- **不展示参考图。** 提案里只有本项目的效果图、平面图、`deck.py` 画的场地示意图、我们做的版面、附录里的白模，以及 `brief/deck-style.json` 里指定的客户 logo。`input/` 和 `brief/media/` 里的任何文件（包括复制件）都不会出现。
- **不讲参考图。** 提案里不出现「上一版方案」「沿用原来的结构」「在上一版基础上升级」「和参考图的关系」这类说法。每个方案只讲它自己：创意、体验、说什么、氛围。

`deck.py check` 会按内容比对图片，并检查这些说法；风格卡 `Do-not-mention:` 一行列出的词也会被拦下。

## 效果图怎么做

图像模型负责想象，skill 负责给它对的输入，并检查它画出来的结果。

- **参考照片直接发给模型。** 客户的上一版方案和客户认可的图片，每次出主视图都作为图片附上（`--ref`），不用文字描述代替。提示词里只说保留什么、在什么基础上升级、不要照搬什么（标语、海报、别家展台）。
- **提示词很短**，大约 200–300 个英文词，只写这些：
  - 想法和主体（两三句）；
  - 品牌色；
  - 三行尺寸：宽深换算成几个人高、整个展台都在一块地台上、主体高度是人的几倍；
  - 一行功能项，以及 logo 的位置（留一块素面板）；
  - 不做顶、不吊挂；
  - 前沿站一个人作比例尺。

  不写机位、灯光、材料，也不写禁用清单，这些会让画面变僵。
- **不让模型画字。** 名字、年份、数字、徽标和 logo 都不让图像模型画：logo 位置留素面板，真实 logo 用 `render.py logo` 贴上或由设计师处理，文字在提案里以文本排出。
- **两张候选，二选一。** 两张是不同的展台，供你选择，不是一套。选定后检查宽、深、主体高度、开口、功能项、有没有多出来的结构、有没有模型画出来的文字、年份、数字或 logo。小问题用一句话修改这张图；尺寸明显不对（偏差超过约 20%）就换另一张或重出。文字改不掉，就在 concept.md 里写一行 `blocked: renders/<文件> – 原因`，这张图不会进提案。
- **正面视图由选定的主视图编辑而来**，所以两张是同一个展台。两张都盖「初稿 – 概念效果示意，不用于施工」章。主推方案还可以加一张细节图，用在材料页。

```bash
R=skills/booth-proposal/scripts/render.py   # 需要 OPENAI_API_KEY，或在 .env 里写 OPENAI_API_KEY= / openai_key=
python $R hero  --prompt hero.txt --ref input/参考1.jpg --ref input/参考2.jpg --out-dir renders --n 2
python $R fix   --base renders/hero-v2.png --add "The stand is too deep: ..." --out-dir renders
python $R front --prompt front.txt --base renders/hero-v2.png --out-dir renders
python $R label renders/hero-v2.png  --title "A · 方案名" --out A-1-hero.png
python $R label renders/front-v1.png --title "A · 方案名" --out A-2-front.png
```

默认模型 `gpt-image-2`，1536 × 1024，高质量；第一次正式出图前先加 `--dry-run` 跑一遍，确认参考图和 key 都读到了（它不发送请求，也不验证 key 是否有效）。一次 `--n 2` 约 2–4 分钟，AI 调用时要给足超时或放到后台，三个方案并行；出错时（key 无效、账号用不了该模型、内容被拒）怎么处理、没有 key 时怎么给提示词包，见 SKILL.md 第 4 步。每张图都会保存实际发送的提示词（`.prompt.txt`）和日志（`.json`）。`render.py logo` 可以把客户的真实 logo 文件贴到展台面板上。每个方案大约需要 2 张候选、0–3 次修图、1 张正面视图，高质量出图每张约 1–2 分钟。

## 提案（第 6 步）

提案是一份 16:9 的 HTML（`pack/proposal.html`），由 `deck.py` 按项目里的文件生成，导出为 `pack/proposal.pdf`。它是给客户看的设计展示：不含工程、工期、人员、报价和场馆技术事项，也不含任何内部工作内容（编号、标书页码、文件名、待办、检查结果、内部备注和风险）。

```bash
D=skills/booth-proposal/scripts/deck.py
python $D new --lead A      # 生成提案骨架；--force 重建，旧版备份到 work/deck-backups/
python $D check             # 有错误就不能导出
python $D render            # 导出 PDF 和预览图（需要 Chrome 或 Edge）
python $D status            # 页数、未完成项、上次检查结果；PDF 比 HTML 旧时提醒
```

页面顺序：封面、目录、项目概况（展会、场馆、日期、展位、开口、限高，配一张 `deck.py` 画的场地示意图）、标书要求（每条写明见第几页）、洞察、展台要说什么、三个方案总览；每个方案一页主图、一页正面图（有可用的正面图才有）、一页体验详情；方案对比；主推方案的分区与动线、材料、屏幕与产品、互动、接待与物料、平面设计（有版面才有）；附录最多 3 页：设计要点回应表、需客户确认的说法、所有方案的平面图。

不会生成：假设表、备选创意表、参考图页、场馆或标书图片、占位页。

**发给客户的只有 `pack/proposal.pdf`。** 不要发项目文件夹或它的压缩包，也不要单发 HTML：文件夹里有标书、参考图和内部卡片。

## 安装

技能在 [`skills/booth-proposal/`](skills/booth-proposal)。脚本需要 Python 3 和 matplotlib、numpy、Pillow；导出 PDF 需要 Chrome 或 Edge：

```bash
pip install -r requirements.txt
```

平面图要显示中文标注时需要中文字体（如思源黑体）；没有的话，平面图改用编号加图例。

- **Claude Code**：`/plugin marketplace add ocrevo/booth-proposal`，再 `/plugin install booth-proposal@ocrevo`；或把 `skills/booth-proposal` 复制到 `~/.claude/skills/`（所有项目）或项目的 `.claude/skills/`。
- **Claude.ai / Claude 桌面版**：下载 [`dist/booth-proposal.skill`](dist/booth-proposal.skill)，在设置的技能（Skills）中上传，并开启代码执行。Claude 本身不出图：接入图像生成工具，或把提示词和参考图拿到图像模型中使用。
- **Codex / ChatGPT**：复制到项目的 `.agents/skills/` 或 `~/.agents/skills/`。ChatGPT 可以直接出图：主视图附上参考照片，正面视图附上选定的主视图。
- **VS Code 中的 GitHub Copilot**：复制到项目的 `.github/skills/` 或 `.agents/skills/`。

## 使用

把标书和参考照片放进对话或工作区，输入 `start`。

| 命令 | 作用 |
| --- | --- |
| `start` | 跑完整个流程 |
| `step mode` | 每步暂停，供你检查 |
| `change <内容>` | 修改假设、尺寸、材质或文字，只重做受影响的部分 |
| `add style` | 补充参考图 |
| `show <项目>` | 查看任一卡片，如 `show brief`、`show frame`、`show geometry B` |
| `render A` | 重新给方案 A 出图 |
| `pack` | 生成或重建提案：`deck.py new`、补全文字、`check` 通过、`render` 导出 PDF |
| `status` | 查看进度、版本和假设，以及提案是否需要重新导出 |

在能写文件的环境里，项目保存在磁盘上：

```
<项目>/
  input/        标书、场馆手册、客户资料、参考照片（不修改）
  brief/        需求卡、场馆卡、框架卡、内容清单、风格卡、ideas.md（之后可复用）；
                design-points.md（提案要回应的设计要点）、deck-style.json（提案的配色、字体、语言和 logo）、
                brand/（客户 logo 文件）、media/（从客户资料里取出的图片，只作参考，不进提案）
  concepts/A/   prompts/、renders/（每次出图及其提示词和日志）、A-1-hero.png、A-2-front.png（选定并盖章的两张）、
                geometry.json、plan.png、白模（附录）、concept.md
  pack/         proposal.html、proposal.pdf（唯一发给客户的文件）、check.txt、preview/、site.svg、boards/
  work/         内部文件，不外发：deck-backups/、提示词包、检查截图
```

## 尺寸核算（第 5 步）

选定效果图后，每个方案写一份几何数据（JSON），它是尺寸的唯一依据：

```bash
S=skills/booth-proposal/scripts
python $S/booth_geometry.py check   geometry.json            # 通过或不通过，并说明原因
python $S/draw_plan.py              geometry.json plan       # plan.png 和 plan.svg
python $S/booth_geometry.py massing geometry.json massing    # 附录用白模，不会发给图像模型
```

核算内容：展位边界、限高与分区限高、元素重叠、通道宽度（0.9 米）与净空（2.1 米）、必需功能项是否齐全、架空构件的支撑和禁止吊挂、重复构件整排是否放得下、复合构件（`group`）按整体核算。不通过就改设计并重新出图。数据格式写在 `booth_geometry.py` 开头。

## 示例与测试

- 虚构客户的完整示例：[`skills/booth-proposal/assets/examples/halvard-example.md`](skills/booth-proposal/assets/examples/halvard-example.md)
- 测试用例：[`skills/booth-proposal/evals/`](skills/booth-proposal/evals)，每次修改 skill 后在新会话里跑一遍。`proposal-deck` 用例专门检查提案：只用自己的图、不讲参考图、没有内部编号和占位页、PDF 与 HTML 一致。

## 局限

- 只到概念阶段，不是施工图，也不替代结构设计和工程确认；功能项尺寸、通道和净空都是经验值，以场馆规定和设计师为准。
- 效果图是演示用的，尺寸以几何数据和平面图为准。效果图上不画文字和 logo：logo 位置留素面板，真实 logo 和文字由 `render.py logo` 或设计师处理。
- 提案只展示设计，不做报价，也不含工期、人员和工程事项。
- 不编造事实：墙上的每一句话都能追溯到客户原文；夸大、受监管或可能过时的说法，在提案里标「需客户确认」，并列入附录。

## 参与贡献

欢迎提交 issue 和 PR。请描述出错的展台场景，并在 `evals/` 中补充测试用例。仓库里只能使用虚构示例，不要提交任何真实客户资料。

## 许可证

[MIT](LICENSE)
