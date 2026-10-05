---
name: ai-video-superpowers-spec-to-plan
version: 2.0.0
description: AI 视频生成+剪辑套件 ai-video-superpowers 第二阶段（v2）。当项目里已有 spec.md（场景片段级脚本，见 brainstorm v2+），用户要求生成执行方案/plan/分段计划/切分片段/写生视频提示词/动作分镜/分镜板/storyboard/预演图时使用。把 spec 的场景片段（SC）切分成固定 15s 的 SEG 视频片段；为每段设计 P01–P12 动作分镜（专业镜头语言）；按故事板模板生成黏土预演分镜板参考图（智核 TT Image）；按分镜重现式模板写出每段视频 prompt 并绑定 @[storyboard]/@[C] 参考图；最后产出 plan.md + plan.html（分镜板审核视图）交用户审核。Use when converting a video spec into an executable generation plan with storyboard previs.
---

# AI Video Superpowers · spec-to-plan

套件第二阶段：读 `spec.md` → 产出 `plan.md` + `plan.html`。**不调用视频生成 API**，但**会调用图片生成 API**（分镜板，走 zhike-image 技能，key=`/var/minis/shared/zhike/image.key`）。项目目录约定见 brainstorm/SKILL.md（共用）。

## 前置

1. 找到项目：用户指定路径，或 `/var/minis/shared/ai-video/*/` 下含 `spec.md` 的项目；多个就问。
2. 读 spec；状态仍是"待审核"时提醒用户先确认 spec。
3. 已有 `plan.md` → 问清重新生成还是迭代（迭代保留已完成 `[x]` 片段）。
4. 新建 `<项目>/storyboards/` 目录（存分镜板）；确认 zhike-image 的 image.key 存在。

## 五步流程

### 1) 切分：固定 15s

- spec 主体是场景片段 SC-xx（剧情/台词/人物/环境，**无机位**——机位是本阶段职责）。
- 每个 SC → `ceil(SC时长/15)` 个 SEG；**每段固定 15s**，动作调度把时长填满（12 格 × ~1.25s）。
- 仅**最后一段**允许 4~14s 兜底；若剩余内容 <4s 不足以成段，并入上一段（该段仍 15s）。
- 切点不切断进行中的动作/对话/运镜；场景大跳优先作切点；每段必须自洽完整。
- 衔接判定（写进每段"衔接"字段）：`独立`（不同时空/无连续动作）/ `连贯（承接 SEG-xx）`（同一段连续剧情）。

### 2) 动作分镜设计：P01–P12

每段 12 个分镜节点，格式 `P## / [镜头标签] / [动作名]: [画面描述]`：

- 镜头标签用专业镜头语言（景别+机位+运动组合），速查表见 `references/storyboard-prompt-template.md`。
- 内容取自 spec 剧情与台词，调度成 12 个定格瞬间：动作弧线递进（蓄力→发力→接触→结果→余韵）、每格每角色仅一种姿态、标明接触点/方向/结果、轴线连续、相邻格机位有变化。
- 台词安排进对应格（谁在说、谁在听、什么姿态）。

### 3) 生成分镜板：`storyboards/SEG-xx.png`

按 `references/storyboard-prompt-template.md` 组装提示词并提交 zhike-image：

```sh
# 提交（挂本段全部人物参考图作外观唯一依据；横版板 16:9、2K、sunburst）
python3 /var/minis/skills/zhike-image/scripts/image.py submit \
  --prompt "<组装好的分镜板模板全文>" --ar 16:9 --res 2K --version sunburst \
  --image refs/char-a.png --image refs/char-b.png
# task_id 立即写入 storyboards/.taskids.json 防丢；轮询：
python3 .../image.py poll --task-id <ID> --timeout 600
# 下载（务必直接落 shared 项目目录）：
python3 .../image.py download --url <result_url> --output storyboards/SEG-01.png
```

- 多段可批量提交后统一轮询（batch 脚本也必须先把 task_id 落盘）。
- 出图核对：12 格齐全、格内无文字箭头、人物比例与朝向全板一致；不合格重试 1 次（微调动作节点描述）。
- 仍失败 → 该段标记"分镜板待补"，继续流程（校验加 `--allow-no-storyboard`），plan.html 显示占位，请用户决定补生成还是跳过。

### 4) 视频提示词（分镜重现式）

按 `references/video-prompt-template.md` 全文填写，核心结构：

- 首段：`@[storyboard] 是本视频的分镜蓝图——请逐镜头进行重现……`（防抽卡规则句照抄不删）
- `@[C]` 人物外观映射句（本段每个出场角色一句）
- 区块：视觉风格/动作语言/视觉特效/摄影风格/音频/环境/情感基调/节奏与递进（取自 spec 第 2 节两栏与氛围设计）
- 分镜节点 P01–P12 逐条写全（机位、景别、人物位置、核心动作、画面细节），与分镜板逐格一致；台词写进对应格
- 连贯片段在"环境"区块加承接句（执行阶段会追加上一段尾帧生成的首帧图）

prompt 内保留 `@[storyboard]`、`@[C1]` 等占位标记；实际文件映射写进该段"参考图"字段：`@[storyboard]=storyboards/SEG-01.png, @[C1 陈岩]=refs/char-chenyan.png, refs/scene-1.png`（@ 标记项仅定义外观；场景图直接写路径）。

### 5) 写 plan.md → 校验 → plan.html → 用户审核

1. 读 `references/plan-template.md` 写 `<项目>/plan.md`，严格保持 `### [ ] SEG-xx` 字段格式（执行阶段依赖打钩结构）。
2. 校验（需全绿）：
   ```sh
   python3 /var/minis/skills/ai-video-superpowers-spec-to-plan/scripts/validate_plan.py <项目>/plan.md
   ```
3. 生成审核页（分镜板大图 + 可折叠/可复制 prompt + 参考图缩略图，依赖 py3-markdown）：
   ```sh
   python3 /var/minis/skills/ai-video-superpowers-spec-to-plan/scripts/make_plan_html.py --project <项目>
   ```
4. 用 `[plan.html](minis://shared/ai-video/<slug>/plan.html)` 展示（移动端可靠的是 HTML 页，不是 md 预览），向用户报：片段数、总时长、分镜板就绪 N/M、衔接判定摘要，请其审核**分镜板质量与 prompt 细节**。确认后把 plan.md 状态改"已审核"，提示下一步 `ai-video-superpowers-plan-to-video`（会按"参考图"顺序传分镜板+人物图）。
