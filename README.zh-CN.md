# booth-proposal

**以设计为先的展台方案 AI 助手，面向展览设计公司。**

上传展台招标书（可附参考图），它会给出三个彼此明显不同的概念方案。每个方案包含核心想法、观众体验、展台要说的话、建筑图纸风格的平面图，以及两张精致的效果图：效果图由图像模型设计，它会直接看到客户自己的参考照片，出图后再对照真实尺寸核对。需求、假设和招标响应对照放在附录。

它是一个 [Agent Skill](https://agentskills.io)：同一个文件夹可在 Claude Code、Claude.ai、Codex、ChatGPT 和 GitHub Copilot 中使用。

[English](README.md)

| 平面图 | 白模（附录） |
| --- | --- |
| ![平面图](skills/booth-proposal/assets/examples/halvard-plan-A.png) | ![白模](skills/booth-proposal/assets/examples/halvard-massing-A-hero.png) |

*来自虚构示例：6 × 4 米转角展位上，75 片格栅一年一片，从 1.2 米升到 4.2 米。*

## 工作方式

**思考时约束在前，展示时设计在前。**

| 步骤 | 内容 | 过关条件 |
| --- | --- | --- |
| 1 简报 | 读标书和全部客户文件；每条要求标出处；缺信息时做假设而不是提问；场馆卡；内容清单 | 每条硬性要求有编号和出处 |
| 2 框架 | 约束分四层；确定功能尺寸；面积预算与进深预算 | 框架卡完整 |
| 3 想法 | 洞察、信息平台；逐张看参考图，说出它属于这个客户的地方；先写五六个一句话想法，再选三个明显不同的；参考图里有客户自己的旧展台时，三个方案中至少两个从它的标志性结构出发 | 通过换 logo 测试，粗略尺寸放得下；参考图里有客户的旧展台时，至少两个方案从它的标志性结构出发 |
| 4 出图 | 三个想法一选定就马上出图（快速开始）：每个方案用短提示词、附上参考照片，出 2 张主视图候选，二选一；目测核对，小问题修图，尺寸不对就重出；正面视图由选定的图编辑而来；两张都盖章 | 尺寸与设计质量检查 |
| 5 深化 | 几何数据 → 核算直到通过 → 平面图、附录用白模 → 内容地图 → 与选定效果图一致的概念文字 → 创意总监点评 | 尺寸核算通过；不通过就改设计并重新出图 |
| 6 方案包 | 设计在前，附录在后 | 每条要求都有交代 |

简报卡和框架卡记录的是项目事实，不属于某一个设计：它们放在 `brief/` 里，可以重复使用，新一轮直接复制，不必重做。

它从不停下来索要缺失的信息：先做有依据的假设，标注出来，继续往下做。之后可以随时修改（例如 `change A1: three sides open`），只重做受影响的部分。

## 安装

技能在 [`skills/booth-proposal/`](skills/booth-proposal)。脚本需要 Python 3 和 matplotlib、numpy、Pillow：

```bash
pip install -r requirements.txt
```

只有平面图要显示中文或日文标注时，才需要中日韩字体（如思源黑体 / Noto Sans CJK）；没有的话，平面图会改用编号，并输出图例。

- **Claude Code（终端、VS Code、JetBrains）**：作为插件安装，`/plugin marketplace add ocrevo/booth-proposal`，再 `/plugin install booth-proposal@ocrevo`；或自己复制文件夹：`skills/booth-proposal` → `~/.claude/skills/booth-proposal`（所有项目）或 `<项目>/.claude/skills/booth-proposal`（单个项目）。
- **Claude.ai / Claude 桌面版**：下载 [`dist/booth-proposal.skill`](dist/booth-proposal.skill)，在设置的技能（Skills）中上传，并开启代码执行。Claude 本身不出图，需要接入图像生成工具，或把提示词包拿到图像模型中使用。
- **Codex / ChatGPT**：复制到 `<项目>/.agents/skills/booth-proposal` 或 `~/.agents/skills/booth-proposal`。Codex CLI、IDE 插件和 ChatGPT 桌面版都会识别；ChatGPT 可以直接出图。
- **VS Code 中的 GitHub Copilot**：复制到 `<项目>/.github/skills/booth-proposal` 或 `<项目>/.agents/skills/booth-proposal`。

## 使用

在对话或工作区中放入标书（以及参考照片），输入 `start`。

| 命令 | 作用 |
| --- | --- |
| `start` | 跑完全部六步 |
| `step mode` | 每步暂停，供你检查 |
| `change <内容>` | 修改假设、尺寸、材质或文字，只重做受影响的部分 |
| `add style` | 补充参考图 |
| `show <项目>` | 查看任一卡片：`show brief`、`show frame`、`show content`、`show geometry B` |
| `render A` | 重新给方案 A 出图 |
| `pack` | 重新生成方案包 |
| `status` | 查看进度、版本和假设 |

在能写文件的 IDE 或智能体环境里，项目会保存在磁盘上：

```
<project>/
  input/        标书、场馆手册、客户资料、参考图
  brief/        需求卡、场馆卡、框架卡、内容、风格卡（之后几轮可重复使用）
  concepts/A/   concept.md、geometry.json、plan.png、白模（附录）、prompts/、renders/、选定的两张效果图
  pack/         方案包
```

可以直接修改 `concepts/B/geometry.json` 再要求重新核算，也可以自己运行脚本。

## 尺寸核算脚本

每个概念都有一份几何数据（JSON），它是尺寸的唯一依据。

```bash
S=skills/booth-proposal/scripts
E=skills/booth-proposal/assets/examples/halvard-geometry-A.json

python $S/booth_geometry.py check   $E          # 通过（PASS）或不通过（FAIL）及原因
python $S/draw_plan.py              $E plan     # plan.png 和 plan.svg
python $S/booth_geometry.py massing $E massing  # massing-hero.png 和 massing-front.png（--views、--size），只用于附录
python $S/booth_geometry.py hints   $E          # 列出每个元素的 render_hint，用于几何数据只能近似表达的形体
```

以下情况算错误，核算不通过：元素超出展位边界、超过限高或分区限高（视线规则）、地面元素重叠、门框式构件开口低于净空高度（2.1 米 / 7 英尺）、必选功能项没有元素承担、场馆禁止吊挂却用了吊挂。以下情况只给警告，不影响通过：通道窄于 0.9 米 / 3 英尺、架空构件没写支撑方式、吊挂尚未得到场馆确认、单面墙悬挑跨度过大。重复构件（`repeat`）整排按一个整体核算，复合构件（`group`）按一个构件核算。白模是从真实机位画出的白色模型，带一个人作比例，只在附录里说明尺寸，绝不发给图像模型。几何数据的格式（`repeat`、`group`、`axis`、`support`、`program`、`required`、`height_zones`、`rigging_allowed`、`render_hint`、`layer`、`camera`）写在 `booth_geometry.py` 开头。

## 效果图

图像模型负责想象，skill 负责给它需要的东西，并核对它画出来的结果。

- **参考照片以图片本身传入**：客户的旧展台和客户喜欢的图片，每次出主视图都作为参考图一起发送（`--ref`），不用文字描述代替。如果其中有客户自己的展台，三个方案中至少两个从它的标志性结构（门框、拱门、背墙）出发，各往不同方向发展，并明显更精致；第三个可以另起炉灶。
- **提示词很短**（约 150–250 词）：两三句话写想法和主体；品牌色；三行尺寸（[宽] × [深] 换算成几个人高，整个展台连同主体都在一块地台上、地台外什么都没有，开口面，主体高度是几个人高）；一行功能项；logo 怎么用；不要顶棚、不要吊挂；几位观众，其中一位站在前沿；再用一句话说明参考图里保留什么、发展什么、哪些不要照搬。不写机位、灯光和材料配方、布局坐标，也不写禁用清单，这些曾让效果图变得拘谨。
- **两张候选，二选一**：每个方案出 2 张主视图候选，选定一张后以画面里的人为比例尺目测宽、深、主体高度，检查开口面、功能项、多余结构、编造或乱码的文字、数量是否正确。小问题用一句修正去编辑这张图；尺寸明显不对（偏差超过约 20%，或主体跑到地台外）就换另一张候选或重出，不修。正面视图由选定的主视图编辑而来，两张是同一个展台。
- **快速开始**：三个方向一选定，几分钟内就出第一批图；几何核算、平面图、内容地图和概念文字随后补上，并与选定的效果图保持一致。

```bash
R=skills/booth-proposal/scripts/render.py      # 需要 OPENAI_API_KEY（或 .env 里写 OPENAI_API_KEY= / openai_key=）
python $R hero  --prompt hero.txt  --ref input/ref-1.jpg --ref input/ref-2.jpg --out-dir renders --n 2
python $R fix   --base renders/hero-v2.png --add "The stand is too deep: ..." --out-dir renders
python $R front --prompt front.txt --base renders/hero-v3.png --out-dir renders
python $R label renders/hero-v3.png  --title "A · Seventy-Five" --out A-1-hero.png
python $R label renders/front-v1.png --title "A · Seventy-Five" --out A-2-front.png
```

默认模型 `gpt-image-2`，1536 × 1024，高质量；加 `--dry-run` 只显示请求内容，不发送。`render.py label` 盖的"初稿"说明，装有中日韩字体时为中英双语，否则只有英文。`render.py logo` 可以在出图后把真实的 logo 文件贴到展板上。每张图都会保存实际发送的提示词（`.prompt.txt`）和日志（`.json`）。每个方案大约需要 2 张主视图候选、最多 3 次修图、1 张正面视图；高质量出图每张 1–2 分钟。

## 示例与测试

- 完整示例（虚构客户）：[`skills/booth-proposal/assets/examples/halvard-example.md`](skills/booth-proposal/assets/examples/halvard-example.md)
- 测试用例：[`skills/booth-proposal/evals/`](skills/booth-proposal/evals)。每次修改后，在新会话中重跑一遍。

## 局限

- 只到概念阶段，不是施工图，也不替代结构设计和工程确认。功能尺寸、通道和净空数值都是经验值，以场馆规定和设计师为准。
- 不做报价。
- 不编造事实：墙上的每一句话都能追溯到客户原文，夸大性说法列入客户确认清单。

## 参与贡献

欢迎提交 issue 和 PR。请描述出错的展台场景，并在 `evals/` 中补充或更新测试用例。仓库中只能使用虚构示例，不要提交任何真实客户资料。

## 许可证

[MIT](LICENSE)
