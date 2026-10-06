# ai-video-sp-skills

Minis (OpenMinis) AI 视频生成 skill 套件，统一在此做版本管理。

本仓库部署位置为 `/var/minis/shared/ai-video-sp-skills/`，各 skill 通过软链接接入
`/var/minis/skills/`，Minis 会照常识别。

## 包含的 skill

| skill | 版本 | 说明 |
|---|---|---|
| ai-video-superpowers-brainstorm | 2.7.0 | 阶段一：访谈收集需求 → spec.md（人物参考图=无头三视图+正脸特写；时长按语速核算 + 子智能体双审） |
| ai-video-superpowers-spec-to-plan | 2.7.0 | 阶段二：spec → plan.md（≤15s 按内容切分、分镜格数由剧情决定、链式分镜板、时长审核子智能体；v2.7 移除俯视调度图环节） |
| ai-video-superpowers-plan-to-video | 1.1.0 | 阶段三：plan → 逐段出片 + ffmpeg-skill 拼接成片 |
| zhike-image | 1.0.0 | 智核 TT Image 2.5 图片生成（文生图/图生图/编辑） |
| zhike-video | 1.0.0 | 智核海螺 H3 视频生成 |

## 流水线

```
brainstorm  →  spec.md   （叙事层：场景片段 SC-01…；时长按台词语速核算）
                └ 双审：参考图完备性 + 时长设计（子智能体循环审到通过）
spec-to-plan → plan.md   （执行层：SEG 切分(≤15s 按内容) + P01–Pxx 分镜(格数由剧情定) + 链式分镜板 + 视频 prompt）
                └ 时长审核：子智能体核台词秒数/分镜密度，循环审到通过
plan-to-video → clips/SEG-xx.mp4 + output/final.mp4
```

关键约定：
- 分镜板按 SEG 顺序**链式**生成（第 2 张起把上一张作连贯性参考图），改某张则其后全部重生成。
- **分镜格数由剧情决定（4~10 格常见，不强行填满 12 格）**，未用格在板面留空白、prompt 只写到 Pxx。
- **时长由内容量决定**（4~15s，台词秒数按对白 3~3.5 字/秒、旁白 3.5~4 字/秒核算），不为凑满 15s 稀释、不为省段数压缩。
- 连贯片段**不再**生成尾帧首帧图——连贯性由 prompt 承接句 + 链式分镜板承担。
- 成片拼接用 **ffmpeg-skill 的 join.py**；iSH 下不要用 ffmpeg concat 解复用器（不转换 list 内路径）。
- 审核任务书模板（spec/plan 共用）：`ai-video-superpowers-spec-to-plan/references/audit-prompt.md`。

## 同步到 Minis 的方式

```sh
for s in zhike-image zhike-video \
         ai-video-superpowers-brainstorm \
         ai-video-superpowers-spec-to-plan \
         ai-video-superpowers-plan-to-video; do
  ln -sfn /var/minis/shared/ai-video-sp-skills/$s /var/minis/skills/$s
done
```

注意：
- API key 不在仓库内（zhike key 存于 `/var/minis/shared/zhike/`）。
- `file_edit` / `file_read` **不跟随软链接**，编辑 skill 文件要用真实路径
  `/var/minis/shared/ai-video-sp-skills/<skill>/…`。
