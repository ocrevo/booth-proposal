# booth-proposal

**展台方案的 AI 设计伙伴，面向展览设计公司。**

## 简介

给它一份展台招标书和一套或几套参考照片，它为每套参考做出几个不同的展台方案，每个方案都有一个想法和一张经过审核的主视图；你从所有方案里自由挑选，选中的方案再做尺寸核算和平面图，最后生成一份提案 PDF，可以直接发给客户。提案默认按招标文件逐条回应（招标回应型），也可以指定为设计展示型；两种都只展示我们自己的设计，从不展示参考图。

它是一个 [Agent Skill](https://agentskills.io)，同一个文件夹可在 Claude Code、Codex、ChatGPT 和 Claude.ai 中使用。

原则：想的时候先讲约束，给客户看的时候只讲设计。模型负责构思、写提示词、做选择和写提案的每一个字；脚本只负责检查、记录、测量和导出，不替你设计，也不跳过任何一步。缺信息时不停下来问，先做合理假设并记下来，之后随时可以改。

## 一次完整的流程

| 步骤 | 模型写什么 | 由谁把关 | 给你看什么 |
| --- | --- | --- | --- |
| 1 简报 | `brief/brief.json`（设计要点、招标条款与交付物、要求的平面稿、需签认的说法、假设，均带出处；可选的提案架构）和阅读笔记 | `gates.py brief --stamp` | 简报报告，加上最可能改变设计的那条假设 |
| 2 框架 | brief.json 里的展位（尺寸、限高、开口、吊挂、功能项）和框架笔记 | `gates.py frame` | 三行说清展位：尺寸与限高、开口、能否吊挂 |
| 3 想法 | 每套参考的想法写进 `brief/ideas.json`，以及展台要说的话 | `gates.py ideas --scaffold` | 每套参考一张想法表，以及出图的张数和时间（含平面稿） |
| 4 出图 | 每个入选想法一段短提示词，brief 要求的每张平面稿一段提示词；在 concept.md、graphic.md 里写 `chosen:` 和 `blocked:` | 每次出图前 `render.py lint`；`gates.py renders` | 每套参考的候选图板、总览和平面稿图板，然后等你选方案 |
| 5 深化 | 选中方案的 `geometry.json` 和内容布置 | `booth_geometry.py check`；`gates.py concepts` | 每个方案的平面图和白模（白模只给你核对尺寸） |
| 6 提案 | 按所选架构写 `deck/storyboard.md` 和 `pack/proposal.html` | `deck.py check`；`deck.py export` | 缩略总览图、第二轮审阅的结论、`pack/proposal.pdf` |

`start` 会把每一步的结果都给你看，然后接着做；整个流程只在一处停下：每套参考的候选图板和总览出来之后，等你选方案。选定后第 5、6 步只针对选中的方案。`step mode` 则每一步都停，等你说继续。

没有图像 API key、也没有导入任何图时，没有可选的方案：`start` 在第 4 步结束，交给你提示词文件、`--dry-run` 命令和导入说明。

## 多套参考与自由选择

参考照片放在 `input/refs/<套名>/` 里，每个文件夹就是一套，照片直接放在文件夹里。`input/` 里的其他文件（标书、场馆手册、logo、产品图）是客户资料，不算参考。

- 每套参考各出几个方案，同一套里的方案必须是不同的展台类型（穿过的门、绕着看的物体、面对的立面、站在下面的顶棚、走进去的房间等）。
- 每个方案出图时附上它这一套的全部照片，可以自由地从中演化，并做得明显更高级。参考只提供形态、空间和氛围；颜色、logo 和内容永远是客户自己的。
- 你在所有套的方案里随便挑，可以跨套，也可以指定主推方案。选择由代码写进 `brief/selection.json`，选择的顺序决定方案在提案里的字母。
- 套名只在内部使用，不会出现在给客户的任何一页上。

```bash
python $S/gates.py select set-1/A set-2/B --lead set-2/B   # 记录选择，主推 set-2/B
python $S/gates.py select --show                            # 查看当前选择
```

（`$S` 指本技能的 `scripts/` 文件夹，命令在项目文件夹里运行，或加 `--project <文件夹>`。）

## 参考图只是输入

参考图是确认过、可以用的设计参考，但提案里**既不展示，也不讲述**：没有参考照片，没有 `input/` 或 `brief/media/` 里的任何文件，也没有一句话讲参考图或「从它演化而来」。每个方案只凭它自己的创意、体验和氛围站住。

这一点由检查强制执行：

- `deck.py check` 按文件内容（哈希）比对提案里的每张图，参考照片、`input/` 和 `brief/media/` 里的文件，即使复制改名也会被拦下（`D-IMG-FORBIDDEN`）；客户 logo 只能来自 `brief/brand/` 或 deck-style 里指定的文件。
- brief.json 的 `do_not_mention` 词条和语言包里的参考类说法出现在页面上就报错（`D-TXT-REFERENCE`）；套名、编号、文件名同样报错（`D-TXT-INTERNAL`）。
- 「延续」「比以前」这类词先挂起，由第一轮冷读逐个判断：是品牌语言就保留，是在讲参考就改写。冷读也会抓出词表抓不到的转述。
- `render.py import` 拒收与参考照片或客户文件内容相同的图（`R-SOURCE`）。

## 效果图

- **只出主视图。** 每个方案出 `candidates_per_concept`（默认 2）张候选，选一张，最多修 `fix_max`（默认 3）次。正面图和细节图不在默认流程里。
- **提示词短而自由。** 按固定的几块来写：想法、品牌色、三行尺寸（换算成几个人高）、功能项，再加几句固定原句（logo 留素面板、画面不出现任何文字、参考图只取形态空间氛围、不照搬）。不写材料、灯光、机位，也不写禁用清单。
- **出图前先过 lint。** 客户名、受保护名称、引号、中文、自由文字里的数字、时间线和周年这类说法、logo 文字说法、别套的照片或已出的图当参考，都会被拦下，一个请求也不会发出。
- **每张图都要审。** 审图的是一个全新的子代理：只给图、切片和展位尺寸，不给提示词、方案名和参考图。代码记录答案并算出结论，三道硬门槛：画面干净（没有文字、数字、名字、类 logo 图形）、尺寸对（宽深在 `size_tolerance` 约 20% 以内，高度不超限）、够高级。只有当前图像的完整审核通过，才能被选中。
- **logo 由代码贴上。** `render.py logo` 把客户的正式 logo 文件贴到留好的素面板上，新图继承原图的审核结果。
- **在别处出的图也能用。** 用 ChatGPT 或 Claude.ai 接入的图像工具出图后，用 `render.py import` 导入，记录来源，审核要求完全一样。
- **平面稿也由图像模型画。** 招标要求设计的平面稿（如展板）写在 brief.json 的 `graphics` 里，每张一个文件夹 `graphics/<GR>/`，用 `render.py graphic` 出图。图像模型只画插画，不画任何文字、数字和 logo，并在提示词指定的一侧（`--area`：上、下、左、右）留出干净的空白；标题和正文在提案里用 HTML 叠在空白处，logo 由 `render.py logo` 合成。产品图只作造型参考，必须重新绘制，原图永远不进提案。审图规则与效果图相同，只是尺寸关卡换成「留白能否放字」（`--text-area`）。平面稿只在招标回应型里使用，设计展示型里 `render.py graphic` 会拒绝。

```bash
python $S/render.py lint --mode hero --prompt concepts/set-1/A/prompts/hero.txt --concept set-1/A --ref input/refs/set-1/r01.jpg
python $S/render.py hero --concept set-1/A --prompt concepts/set-1/A/prompts/hero.txt --ref input/refs/set-1/r01.jpg --dry-run
python $S/render.py import 下载的图.png --concept set-1/A --ref input/refs/set-1/r01.jpg --prompt concepts/set-1/A/prompts/hero.txt
python $S/render.py graphic --graphic GR1 --prompt graphics/GR1/prompts/graphic.txt --area top --ref input/product.png --dry-run
python $S/gates.py renders --graphic GR1                    # 检查平面稿的选定图和审核
```

默认模型 `gpt-image-2`、1536×1024、高质量。key 读环境变量 `OPENAI_API_KEY`，或项目文件夹及上级文件夹里 `.env` 的 `OPENAI_API_KEY=` 一行。平面稿的尺寸按 brief 里的比例取最接近的一种（竖版 1024×1536、方形 1024×1024、横版 1536×1024）。每张图都是付费的：第一次出图前先用 `--dry-run` 看一遍，并先告诉你张数和大致时间（`gates.py report ideas`，平面稿按张数 × 每张候选数计入）。

## 提案

提案只有一个来源：`pack/proposal.html`，16:9 页面，由模板的版式拼成，每一个字都由模型写在 HTML 里，再导出成 `pack/proposal.pdf`。不论哪种架构，提案都不含工程与结构、场馆技术事项，不写任何工期、人数、价格数字，也不含任何内部内容（brief 的内部编号、出处、文件名、套名、待办、检查结果）；招标自己的条款编号可以写在页上。

### 两种提案架构

架构就是提案的章节方案，每种登记为 skill 里的一份定义（`assets/architectures/<id>.json`）。现在有两种：

| | 招标回应型 `tender`（默认） | 设计展示型 `showcase` |
|---|---|---|
| 何时使用 | 不指定时一律用它；brief 没有编号条款时也用它，按设计要点的顺序排 | 只在明确指定时 |
| 排序依据 | 跟随招标：复述需求，逐条回应条款 | 设计叙事：需求、洞察、方案、比选、主推方案深化 |
| 章节 | 封面、项目理解、设计方案、附录总是必需；互动方案、平面设计、另行提交由 brief 触发（见下表）；缺必需章节报错，顺序不对给警告 | 全部可选，顺序只是建议；`deck.py new` 只写封面 |
| 回应表 | 每条条款、每项交付物一行，指向回应它的页 | 每个设计要点一行 |
| 工期、人员、报价 | 招标要求时只放一页「另行提交」，不写任何内容和数字 | 不出现 |
| 平面稿 | brief 要求时每张一页 | 不放（`D-IMG-FORBIDDEN` `kind`），也不出图 |

怎样选：

- 聊天里说 `start`，用默认的招标回应型；说 `start showcase`（或「用设计展示型」），先写入架构再开始；中途换用 `architecture <id>`。
- 选择写在 brief.json 的 `proposal.architecture`（项目也可以在 `brief/deck-style.json` 的 `thresholds.architecture` 里覆盖默认值）。名字不存在时 `gates.py brief` 报 `G-BRIEF`（`architecture`），并列出已有的架构。
- 已经有提案时换架构，用 `deck.py new --force` 按新架构重建骨架，旧的提案移到 `work/backup/`。

```bash
python $S/gates.py architectures            # 列出已有架构：简介、回应表排法、可用图片类型、章节及必需条件
python $S/gates.py architectures --json     # 同上，机器可读
```

两种架构的来历、与国际常见做法的三方对照，见 [docs/proposal-architectures.md](docs/proposal-architectures.md)。

### 招标回应型提纲（架构 B，默认）

章节是通用的：可选章节只由 brief 自己的条款（`clauses`，带招标编号）、交付物（`deliverables`，没有编号的「提案须包含」）和平面稿清单（`graphics`）触发，不带任何具体招标的定制内容。细节见 [arch-tender.md](skills/booth-proposal/references/arch-tender.md)。

| # | 章 | 何时必需 | 内容 |
|---|---|---|---|
| 1 | 封面 `cover` | 总是 | 提案标题、主效果图、客户与展会 |
| 2 | 项目理解 `understanding` | 总是 | 项目与展会复述、展位规格（可选自绘 `site.svg`）、用平实的话说清招标要什么 |
| 3 | 设计方案 `design` | 总是 | 方案板、平面图、标注图，几个方案时加比选；然后按条款顺序，每条设计条款一页或一组，页上可以写招标的条款编号 |
| 4 | 互动方案 `interaction` | 有互动类条款或交付物 | 观众做什么、内容、动线 |
| 5 | 平面设计 `graphics` | brief 列了平面稿，或有平面类条款 | 每张平面稿一页（`graphic` 或 `graphic:wide` 版式）：选定的插画，标题和正文用 HTML 叠在留白处，旁边写挂在哪里、说什么；缺页报错 |
| 6 | 另行提交 `separate` | 有工期类（execution）或报价类（price）条款或交付物 | 只有一页，由 `deck.py new` 生成：标题、固定句「执行工期、现场人员与报价另行提交。」，以及这些条款和交付物的清单；不能加别的文字，任何工期、人数、价格数字都报错（`D-NUMBER` `separate`） |
| 7 | 附录 `appendix` | 总是 | 回应表：每条条款、每项交付物一行（条款编号、我们的回应、页码）；工期和报价类指向另行提交页，混合条款同时指向设计页和另行提交页；然后是待客户确认的表述 |

每条设计要点都应落在某条条款或交付物的 `points` 里，否则 `gates.py brief` 和 `deck.py check` 给出 `coverage` / `points` 警告。

### 设计展示型提纲（架构 A，需指定）

内容与以前相同。建议顺序，正文约 12–16 页（细节见 [arch-showcase.md](skills/booth-proposal/references/arch-showcase.md)）：

| # | 部分 | 内容 |
|---|---|---|
| 1 | 封面 | 最强的一张主效果图、方案名、展会信息 |
| 2 | 目录 | 各章标题 |
| 3 | 项目概况 | 展会、展位尺寸与开口；可选一张自绘场地示意 `site.svg`（展位轮廓、开口、主通道，不含任何方案元素） |
| 4 | 需求回应 | 每个设计要点用平实的话写一句，注明在第几页回答 |
| 5 | 洞察与展台要说的话 | 洞察、主信息与信息层级 |
| 6 | 方案总览 | 入选方案并排：效果图、方案名、一句话宣言 |
| 7 | 每个入选方案一章 | **方案板**：主效果图、方案名、一句话宣言、想法；**体验细节**：10 米外、3 米内、走进来、拍照点，主标题与至多三条信息，氛围；**平面图**：编号分区、关键数据（尺寸、最高点、开口） |
| 8 | 方案比选 | 每个方案只写「为什么选它」和「深化方向」，主推方案带「推荐」标记 |
| 9 | 主推方案深化 | 带标注的效果图（图上标点说明屏幕、产品、柜台、互动、接待），再加材料、互动或文字页 |
| 10 | 附录（至多 3 页） | 设计要点回应表（要点、各方案的回应、页码）；待客户确认的表述（品牌数据、荣誉等带标记的说法及所在页） |

每种页面可用的版式（`deck.py layouts` 列出全部，`--emit` 给出片段）：

| 页面作用 | 版式 |
|---|---|
| 封面 | `cover:bleed`、`cover:split` |
| 目录、章节页 | `agenda`、`divider` |
| 总览、方案板 | `overview`；`board`、`board:bleed`、`board:mirror`、`image`、`stage` |
| 平面图、标注图 | `plan`；`annotated` |
| 文字、材料、互动 | `statement`、`cards:n2/n3/n4/n6`、`detail`、`facts`、`flow`、`gallery:g1–g4`、`free` |
| 比选 | `compare` |
| 回应表、确认清单 | `table`（回应表也可用 `cards`） |
| 平面稿（招标回应型） | `graphic`、`graphic:wide`（`--emit graphic --graphic GR1` 直接填好图和留白位置） |
| 另行提交（招标回应型） | `statement:separate`（由 `deck.py new` 生成，brief 改了以后重新 `--emit statement:separate --chapter separate` 替换） |

两种架构的提案里都永远不放：参考图、白模、工程与结构，工期、人员、报价的任何内容或数字（招标回应型只说明另行提交），以及任何内部编号和文件名。

国际展览与品牌体验公司的提案通常包含哪些部分，以及与本提纲的对照，见 [docs/proposal-strategies.md](docs/proposal-strategies.md)。

### 制作流程

1. 先写 `deck/storyboard.md`，每页一行：所属章节、作用、要回应哪些条款或设计要点、用哪张图。
2. `deck.py new` 按当前架构生成外壳和章节骨架（每章第一页带 `data-chapter`），`deck.py layouts --emit` 给出每种版式的片段（`--chapter` 设定所属章节），粘进去填字。
3. `deck.py check`（只读）找错，`deck.py render` 生成预览、缩略总览图并测量溢出，循环到零错误、零溢出。
4. 两轮审阅：第一轮只读文字的冷读（有没有讲参考、有没有内部笔记、每个设计要点在哪页有原句回应）；第二轮图文对照（文字说的和图上看到的、和几何数据是否一致；平面稿上叠的字是否易读，`D-LAYOUT` `legibility` 警告在这里处理）。结果用 `deck.py review --record` 记录。
5. `deck.py export`：检查有错、渲染过期或有溢出、审阅缺失或过期、第二轮还有没解决的问题，都会拒绝导出。

`pack/` 只允许放 `proposal.html`、`proposal.pdf`、`site.svg`，其他生成的文件都在 `work/`。**发给客户的只有 `pack/proposal.pdf`**，不要发文件夹、压缩包或 HTML。

## 安装

技能在 [`skills/booth-proposal/`](skills/booth-proposal)。脚本需要 Python 3 和 matplotlib、numpy、Pillow；导出 PDF 需要 Chrome 或 Edge：

```bash
pip install -r requirements.txt
```

平面图要显示中文标注时需要中文字体（如思源黑体）；没有的话，平面图改用编号加图例。

- **Claude Code**：`/plugin marketplace add ocrevo/booth-proposal`，再 `/plugin install booth-proposal@ocrevo`；或把 `skills/booth-proposal` 复制到 `~/.claude/skills/`（所有项目）或项目的 `.claude/skills/`。出图用 `render.py` 和 OpenAI key；没有 key 时用 `render.py import` 导入别处出的图。审图交给子代理。
- **Codex**：复制到项目的 `.agents/skills/` 或 `~/.agents/skills/`，用法同 Claude Code；没有子代理时，在新一轮对话里自己审，并记为 `self`。
- **ChatGPT**：同样放进 `.agents/skills/`。ChatGPT 可以直接出图：把提示词文件和这一套的参考照片一起给它，再用 `render.py import` 导入。有浏览器时得到 PDF；没有时交给你检查过的 HTML，在 Chrome 或 Edge 里打印成 PDF（无边距、打开背景图形）。
- **Claude.ai / Claude 桌面版**：下载 [`dist/booth-proposal.skill`](dist/booth-proposal.skill)，在设置的技能（Skills）里上传，并开启代码执行。Claude 本身不出图：接入图像工具，或把提示词和参考图拿到图像模型里用，再导入。开着代码执行时交给你检查过的 HTML 自行打印；关掉时只给提示词、手工核对的简报和文字版提案，并说明哪些检查没跑。

## 使用

把标书和参考照片放进对话或工作区（参考照片按套放进 `input/refs/<套名>/`），输入 `start`。命令可以直接打，也可以用任何语言的自然话说。

| 命令 | 作用 |
| --- | --- |
| `start [架构]` | 跑完整个流程，只在选方案前停一次；不写架构就用招标回应型，写了（如 `start showcase`）先记进 brief.json 再开始 |
| `step mode` | 每一步都停，等你说继续 |
| `architecture <id>` | 换提案架构：写入 brief.json，跑 `gates.py brief`；已有提案时用 `deck.py new --force` 重建（`gates.py architectures` 列出可选的） |
| `change <内容>` | 修改假设、尺寸、参考或文字，只重做受影响的部分 |
| `add set <名字>` | 新增一套参考：照片放进 `input/refs/<名字>/`，只为这一套做想法和出图，再给你看它的图板和总览 |
| `select <套>/<方案> … [lead <套>/<方案>]` | 选定要深化的方案和主推方案（`gates.py select`），然后做第 5、6 步 |
| `show <项目>` | 完整查看某份报告、笔记、图板或图片，如 `show brief`、`show selection` |
| `render <套>/<方案>` | 重新给这个方案出图；`render GR1` 重出一张平面稿 |
| `pack` | 第 6 步：生成或更新提案、检查、渲染、审阅、导出 |
| `status` | 每步进度、提案架构、未确认的假设、当前选择和提案状态 |

## 项目文件夹

```
<项目>/
  .env                        可选，放 API key，永不外发
  input/                      客户资料：标书、手册、logo、产品图（不是参考）
    refs/<套名>/              每套参考一个文件夹，照片直接放里面
  brief/                      brief.json、ideas.json、deck-style.json、阅读笔记（*.md）
                              selection.json（只由代码写）、brand/（正式 logo）、media/（从文件里取出的图，不展示）
  concepts/<套名>/<方案>/     concept.md、prompts/hero.txt、renders/（每张图连同提示词、记录和审核）
                              选中方案另有 geometry.json、平面图；白模只供内部核对
  graphics/<GR>/              brief 要求的每张平面稿：graphic.md、prompts/graphic.txt、renders/
  deck/storyboard.md          提案分镜
  pack/                       只放 proposal.html、proposal.pdf、site.svg
  work/                       其他所有生成文件：检查、预览、切片、图板、备份
```

哈希、时间戳、图片记录、审核结果、参考印记和方案选择都只由代码写，不要手改。

## 尺寸核算

尺寸以选中方案的 `geometry.json` 为唯一依据，效果图只是目测。格式写在 `booth_geometry.py` 开头的说明里。

```bash
python $S/booth_geometry.py check concepts/set-1/A/geometry.json                          # 直到 RESULT: PASS
python $S/draw_plan.py plan concepts/set-1/A/geometry.json concepts/set-1/A/plan           # plan.png / .svg / .json
python $S/booth_geometry.py facts concepts/set-1/A/geometry.json                          # 尺寸、分区、功能项（JSON）
python $S/gates.py concepts                                                                # 检查所有选中方案
```

核算内容：是否超出展位和限高、分区限高、构件重叠、门洞净空、能否吊挂、必需功能项是否齐全，以及通道和支撑的提醒。`gates.py concepts` 还会核对几何数据与简报里的展位是否一致，确实要不同时需写明理由；平面图比几何数据旧也会报出来。核算不通过就改设计、更新数据、重新出图，让图、平面图和文字说的是同一个展台。提案里写的尺寸和数量都取自 `facts`。

## 测试与评测

```bash
pip install -r requirements-dev.txt
python -m pytest -q                                        # 文档、脚本和发布测试
python tools/build_eval_fixtures.py --all                  # 生成评测用的虚构参考图和项目
python tools/eval_grade.py --case <用例> --workspace <目录>   # 对一次评测运行做确定性检查
python tools/scan_client_terms.py                          # 扫描仓库里不该出现的客户用词
```

评测用例在 `skills/booth-proposal/evals/`，说明见那里的 README。只有 `reference-first` 会真正调用付费的图像接口，其他用例请在没有 `OPENAI_API_KEY` 的环境里跑。

## 局限

- 只到概念阶段，不是施工图，不替代结构设计和工程确认；功能项尺寸、通道和净空都是经验值，以场馆规定和设计师为准。
- 效果图的尺寸和品质由模型审图判断，不是测量；真正的尺寸以几何数据和平面图为准。
- v2 的测试和评测没有用真实的图像 API key 跑过，效果图和平面稿都只验证到 lint 和 `--dry-run`。
- 招标回应型只按 brief 里记下的条款、交付物和平面稿搭章节；条款归类（设计、互动、工期、报价等）由模型读标书时判断，脚本不读原始标书。
- HTML 导出 PDF 需要本机有 Chrome 或 Edge；没有时只能交出 HTML，由你自己打印。
- 不编造事实：墙上的每一句话都能追溯到客户原文；夸大、受监管或可能过时的说法在提案里标「需客户确认」，并列入附录。

## 参与贡献

欢迎提交 issue 和 PR。请描述出错的展台场景，最好在 `skills/booth-proposal/evals/` 里补一个用例。仓库里只能使用虚构材料（Nordvik Ferries、Tidewater Pass、Ostara Coffee），不要提交任何真实客户的资料、名称或项目用词；提交前运行 `python tools/scan_client_terms.py`，必须通过。修改技能后请重新生成 `dist/booth-proposal.skill`（`python tools/build_dist.py`）。

## 许可证

[MIT](LICENSE)
