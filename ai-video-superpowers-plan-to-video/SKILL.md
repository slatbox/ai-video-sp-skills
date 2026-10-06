---
name: ai-video-superpowers-plan-to-video
version: 1.2.0
description: AI 视频生成+剪辑套件 ai-video-superpowers 第三阶段（执行）。当项目已有 plan.md，用户要求开始生成视频/按 plan 逐段生成/执行视频计划/生成视频片段并拼接成片时使用。开始前报计划（段数/消耗）并询问生成方式：一次性生成 or 一个一个生成；按 plan 顺序调用海螺 H3 生成每段视频（断点续跑、每段完成在 plan 打钩），每段按 plan 的"参考图"字段挂分镜板+人物图+场景图（分镜板已链式连续，连贯片段无需再生成尾帧首帧图）；全部完成后用 ffmpeg-skill 的 join.py 拼接输出 output/final.mp4。Use when executing a video plan: generating clips with hailuo and stitching the final video with the ffmpeg skill.
---

# AI Video Superpowers · plan-to-video

套件第三阶段：执行 `plan.md` → 逐段生成 `clips/SEG-xx.mp4` → 拼接 `output/final.mp4`。项目目录约定见 `ai-video-superpowers-brainstorm/SKILL.md`（共用）。

## 前置

1. 找到项目与 `plan.md`（用户指定，或 `/var/minis/shared/ai-video/*/` 下唯一含 plan 的项目）。plan 若"待审核"，先请用户审核确认再消耗额度。
2. 先跑 `validate_plan.py`（路径见 spec-to-plan 技能）确认格式可用。
3. **断点续跑**：`### [x]` 的片段已有 `clips/` 成片则跳过；只处理 `### [ ]` 的片段。开始前向用户报计划：共 N 段、待生成 M 段、预计消耗（时长按秒计费），并**询问生成方式**：
   > 生成方式选哪种？
   > 1. **一次性生成**——全部段并行/连续提交，一次性跑完（快，中途不用管）
   > 2. **一个一个生成**——逐段提交、每段出片后给你过目再继续（稳，出问题早发现）
   >
   > 回复数字即可。
   按用户选择执行：选 1 则连续提交全部段（轮询仍可分批做）；选 2 则严格逐段——每段出片、验收、向用户简报后，等用户点头（或无异议）再提交下一段。
4. 调用细节先读 `/var/minis/skills/zhike-video/SKILL.md`（视频 key=`/var/minis/shared/zhike/.key`）与 `/var/minis/skills/zhike-image/SKILL.md`（图片 key=`.../image.key`）。HTTP 走两技能自带脚本（内部用 curl），不要用 Python urllib。

## 逐段生成（按 plan 顺序）

对每个未完成片段：

1. **参考图准备**：直接用 plan 的"参考图"字段列出的图（分镜板 + 人物图 + 场景图），按顺序全部作为 `--image` 传入。
   分镜板已按 SEG 顺序链式生成（每张与上一张视觉连续），**连贯片段不再生成尾帧首帧图**——连贯性由 prompt 的承接句 + 链式分镜板的一致性承担，无需 frames/ 首帧。
2. **选模型**：本段参考图非空 → `hailuo-h3-quannengcankao`（需 ≥1 图）；否则 → `hailuo-h3`。ar/res/duration 均取自 plan。
3. **提交 + 轮询**：
   ```sh
   python3 /var/minis/skills/zhike-video/scripts/video.py submit \
     --model <model> --prompt "<plan 中该段 prompt>" --duration <4~15> \
     --ar <画幅> --res <分辨率> --image <refs/xxx.png 可多个>
   # → task_id 在 stdout 首行（格式 `task_id = 160560631`）；轮询（视频常 5~60 分钟）：
   python3 .../video.py poll --task-id <ID> --timeout 780
   ```
   轮询用 shell_execute 的 `delay`/timeout 链反复跑（单次 shell 超时 ≤900s），直到 `is_final`；一次没完就再跑一轮 poll。>70 分钟仍 pending 视为上游拥堵，告知用户。
4. **下载与验收**：`download --url <result_url> --output clips/SEG-02.mp4`；用 ffprobe 核对时长与 plan 相差 ≤1s，明显不对（黑屏/时长异常）则重试一次（微调 prompt），仍失败标记问题请用户决定。
5. **打钩**：验收通过后立刻用 file_edit 把 `### [ ] SEG-02` 改成 `### [x] SEG-02`（进度持久化，中断可续跑）。段失败不打钩，在其备注行追加 `<!-- 失败: 原因 -->`。

片段生成较长，边做边向用户简报进度（第 x/N 段、状态）。生成期间不要空转等待——用 `delay` 链轮询。

## 拼接成片

全部 `SEG` 打钩后，用 **ffmpeg-skill 的 join.py** 拼接（统一分辨率/帧率/音频并校验各段与总时长）：

```sh
cd <项目根>/clips
python3 /var/minis/skills/ffmpeg-skill/scripts/join.py SEG-01.mp4 SEG-02.mp4 SEG-03.mp4 ... \
  --transition none -o <项目根>/output/final.mp4
# → output/final.mp4，join.py 打印实际时长与校验结果
```

需要转场时加 `--transition fade --duration 1`（xfade 转场会自动重编码）。

**不要用本技能的 concat.py 或 ffmpeg concat 解复用器**：iSH 下 ffmpeg 只转换命令行参数里的路径，list.txt 内容里的 `/var/minis/...` 路径不会被转换，必然报 `Impossible to open`。join.py 把各段直接作为命令行输入，因此可正常工作。

完成后把 plan 底部"拼接"行也打钩，用 `[final.mp4](minis://...)` 给用户，并提示可用 `ffmpeg-skill` 做后期（配乐、字幕、转场、裁剪调色）。

## 失败与重试

- `state=failed` 自动退款：重试 1 次（精简 prompt/换模型），再失败把片段连同错误留在 plan 备注里，问用户继续还是调整。
- 任何中断（会话/超时）都不丢进度：进度只认 plan.md 的勾 + clips/ 成片，重跑本技能即续。
