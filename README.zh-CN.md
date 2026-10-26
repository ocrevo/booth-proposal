# booth-proposal

**以设计为先的展台方案 AI 助手，面向展览设计公司。**

上传展台招标书（可附参考图），它会给出三个来自不同设计路线的概念方案。每个方案包含核心想法、观众体验、墙面信息、建筑图纸风格的平面图、白模，以及按真实尺寸锁定的两张效果图。需求、假设和招标响应对照放在附录。

它是一个 [Agent Skill](https://agentskills.io)：同一个文件夹可在 Claude Code、Claude.ai、Codex、ChatGPT 和 GitHub Copilot 中使用。

[English](README.md)

## 工作方式

**思考时约束在前，展示时设计在前。**

| 步骤 | 内容 | 过关条件 |
| --- | --- | --- |
| 1 简报 | 读标书和全部素材；每条要求标出处；缺信息时做假设而不是提问；提取内容 | 每条硬性要求有编号和出处 |
| 2 框架 | 约束分四层；确定功能尺寸；面积预算与进深预算 | 框架卡完整 |
| 3 想法 | 洞察、信息平台、参考图分析；先发散五六个想法，再选三个 | 通过换 logo 测试，粗略尺寸放得下 |
| 4 深化 | 几何数据 → 核算 → 平面图与白模 → 内容地图 → 概念文字 → 创意总监点评 | 尺寸核算通过 |
| 5 出图 | 在白模上生成主视图和正面视图 | 一致性与设计质量检查 |
| 6 方案包 | 设计在前，附录在后 | 每条要求都有交代 |

## 安装

技能在 [`skills/booth-proposal/`](skills/booth-proposal)。脚本需要 Python 3 和 matplotlib、numpy：`pip install -r requirements.txt`。平面图要显示中文标注，需要安装中文字体（如思源黑体）；没有的话，平面图会改用编号加图例。

- **Claude Code**：`/plugin marketplace add ocrevo/booth-proposal`，再 `/plugin install booth-proposal@ocrevo`；或把文件夹复制到 `~/.claude/skills/` 或项目的 `.claude/skills/`。
- **Claude.ai / Claude 桌面版**：下载 [`dist/booth-proposal.skill`](dist/booth-proposal.skill)，在设置的技能（Skills）中上传，并开启代码执行。Claude 本身不出图，需要接入图像生成工具，或把提示词和白模拿到图像模型中使用。
- **Codex / ChatGPT**：复制到项目的 `.agents/skills/` 或 `~/.agents/skills/`。ChatGPT 可以直接出图。
- **VS Code 中的 GitHub Copilot**：复制到项目的 `.github/skills/` 或 `.agents/skills/`。

## 使用

在对话或工作区中放入标书，输入 `start`。

常用命令：
- `step mode`：每步暂停，供你检查。
- `change`：修改假设、尺寸、材质或文字，只重做受影响的部分。
- `add style`：补充参考图。
- `show`：查看任一卡片。
- `render`：重新出图。
- `pack`：重新生成方案包。
- `status`：查看进度。

在 VS Code 等能写文件的环境里，项目会按 `input/`、`brief/`、`concepts/A/`、`pack/` 的结构保存。设计师可以直接修改 `geometry.json`，再重新核算。

## 尺寸核算

每个概念都有一份几何数据（JSON），它是尺寸的唯一依据。核算会检查以下各项：
- 展位边界、限高与分区限高（视线规则）
- 元素重叠
- 通道宽度（0.9 米 / 3 英尺）与净空高度（2.1 米 / 7 英尺）
- 必选功能项是否齐全
- 架空构件的支撑方式，以及是否违反"禁止吊挂"
- 重复构件（例如 75 片格栅）整排是否放得下

用法见英文说明中的 "The geometry scripts"。

## 局限

- 只到概念阶段，不是施工图，也不替代结构设计和工程确认；尺寸规则都是经验值，以场馆规定和设计师为准。
- 不做报价。
- 不编造事实：墙上的每一句话都能追溯到客户原文，夸大性说法列入客户确认清单。

## 参与贡献

欢迎提交 issue 和 PR。请描述出错的展台场景，并在 `evals/` 中补充测试用例。仓库中只能使用虚构示例，不要提交任何真实客户资料。

## 许可证

[MIT](LICENSE)
