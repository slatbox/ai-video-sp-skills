---
name: ai-video-superpowers-spec-to-plan
version: 1.0.0
description: AI 视频生成+剪辑套件 ai-video-superpowers 第二阶段。当项目里已有 spec.md（场景片段级脚本，见 brainstorm v2），用户要求生成执行方案/plan/分段计划/切分片段/写生视频提示词时使用。把 spec 的场景片段（SC）按单片段最长 15s 切分成 SEG 片段，由本阶段决定机位/景别/镜头运动（分镜是执行层概念，在 plan 中落地），为每段生成生视频提示词、挂接参考素材、判定相邻片段的衔接策略（独立 or 连贯），写出 plan.md 并用校验脚本检查，待用户审核。Use when converting a video spec into an executable generation plan.
---

# AI Video Superpowers · spec-to-plan

套件第二阶段：读入 `spec.md` → 产出可直接执行的 `plan.md`。**不调用视频生成 API**。项目目录约定见 `ai-video-superpowers-brainstorm/SKILL.md`（共用）。

## 前置

1. 找到项目：用户指定路径，或在 `/var/minis/shared/ai-video/*/` 下找含 `spec.md` 的项目；有多个就问。
2. 读 spec；若 spec 状态仍是"待审核"，提醒用户先确认 spec。
3. 若已有 `plan.md`，问清是重新生成还是迭代（迭代先读入，保留已完成 `[x]` 片段的成果路径）。

## 切分规则（单片段 ≤15s）

- spec 的主体是**场景片段（SC-01…）**：每场戏含剧情、时长、台词、人物、环境，但**不含机位/景别/镜头运动**——那些是本阶段的职责，切分时由你决定并写进各 SEG 的提示词（镜头运动）与画面内容。
- 一个 SEG 片段 = 1 个场景片段的全部，或 1 个较长场景片段切成的多段相邻片段，总时长 **4~15s**（模型最短 4s，尽量凑到 10~15s 省成本）。
- **不切断正在进行的动作、对话和运镜**；场景/机位大跳的地方最适合作为切点。
- 每个片段必须**自洽完整**：单看一段也能理解画面，不依赖上下文。
- 片段总时长与 spec 目标时长一致（±10%）。

## 提示词写法

每段一个独立 prompt，按《主体 + 场景/动作 + 风格 + 光线氛围 + 镜头运动》组织，素材直接取自 spec 场景片段的剧情/台词/环境描述列，补上风格/人物一致性描述（人物外观细节要写进每段，模型无记忆；画面风格与氛围风格分开取自 spec 第 2 节两栏）。中文即可。有台词的段落把台词写进 prompt。

## 参考素材挂接

- 每段列出需要的参考图（人物形象图、场景图、风格图，来自 spec 参考素材表），路径为相对项目根的 `refs/...`。
- 执行阶段将用 `hailuo-h3-quannengcankao`（需至少 1 图）传入；无任何参考图的段落用 `hailuo-h3` 纯文生视频。

## 相邻片段衔接判定（写进每段的"衔接"字段）

- `独立`：两段各自完整、可跳切（spec 中分属不同场景片段/时空/无连续动作）→ 无需衔接素材。
- `连贯`：同一段连续剧情/动作 → 标注 `连贯（承接 SEG-xx）`。执行阶段会自动：提取上一段尾帧 → 生成不同机位的首帧图 → 作为本段参考素材。plan 里只需标记，不预生成。

## 输出 plan.md

读模板 `/var/minis/skills/ai-video-superpowers-spec-to-plan/references/plan-template.md` 写入 `<project>/plan.md`，严格遵守模板字段与 `### [ ] SEG-01` 格式（校验脚本与执行阶段都依赖它）。

写完必跑校验（需全绿才请用户审核）：

```sh
python3 /var/minis/skills/ai-video-superpowers-spec-to-plan/scripts/validate_plan.py <project>/plan.md
```

校验通过后向用户展示：片段数、总时长、衔接判定摘要、参考图清单，明确请其审核 `plan.md`；确认后提示下一步 `ai-video-superpowers-plan-to-video`。
