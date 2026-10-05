# 视频 Plan · <项目名称>

> 由 ai-video-superpowers-spec-to-plan 生成；plan-to-video 按此执行并打钩。状态：待审核 / 已审核
> 来源 spec：spec.md ｜ 总时长：xx s ｜ 片段数：N ｜ 画幅：16:9 ｜ 分辨率：1080P ｜ 分镜板：N 张（storyboards/）

## 默认生成参数

- model：hailuo-h3-quannengcankao（每段必带分镜板+人物参考图）
- duration：按内容量 4~15s（上限 15s 硬限制，时长设计以时长审核结论为准）｜ ar：<画幅> ｜ res：768P（试稿）/ 1080P（成品）

## 片段列表

### [ ] SEG-01
- 时长: xs（时长依据：台词约 xs + 动作 N 格，审核通过）
- 来源场景片段: SC-xx
- 衔接: 独立（开场，无上一段）
- 分镜板: storyboards/SEG-01.png（P01–Pxx 黏土预演，4×3 网格，仅用 N 格其余空白）
- 分镜概览: P01 大远景… → Pxx …（一行 N 节点速览，供快速审核）
- prompt: |
  @[storyboard] 是本视频的分镜蓝图——请逐镜头进行重现。……
  （references/video-prompt-template.md 模板全文填好，分镜节点 P01–P12 逐条写全）
- 参考图: @[storyboard]=storyboards/SEG-01.png, @[C1 角色名]=refs/char-a.png, @[C2 角色名]=refs/char-b.png（场景图直接写路径 refs/scene-1.png，不带 @ 标记）
- 成片: clips/SEG-01.mp4
- 备注: 台词/特殊要求（可选）

### [ ] SEG-02
- 时长: xs
- 来源场景片段: SC-yy
- 衔接: 连贯（承接 SEG-01）← 连贯关系靠 prompt 环境区块的承接句 + 分镜板链式一致保证，**不再生成尾帧首帧图**
- 分镜板: storyboards/SEG-02.png（P01–Pxx 黏土预演，仅用 N 格其余空白）
- 分镜概览: ...
- prompt: |
  ...
- 参考图: @[storyboard]=storyboards/SEG-02.png, @[C1 角色名]=refs/char-a.png, refs/scene-1.png
- 成片: clips/SEG-02.mp4

<!-- 依次 SEG-03...；最后加一行：
- [ ] 全部片段完成
 -->

## 审核记录

- 时长审核（子智能体）：第 x 轮通过 ｜ 结论摘要（台词可说完 / 密度合理）
- 分镜格数：各段 P01–Pxx，格数由剧情决定，板面剩余格留空白

## 成片

- [ ] 拼接（用 ffmpeg-skill 的 join.py，按其 SKILL.md 调用）：
  `python3 /var/minis/skills/ffmpeg-skill/scripts/join.py clips/SEG-01.mp4 clips/SEG-02.mp4 ... --transition none -o output/final.mp4`
  （先 `cd <项目根>/clips` 再传文件名最稳；join.py 会统一分辨率/帧率/音频并做校验。iSH 下不要用 concat.py 或 ffmpeg concat 解复用器——它不转换 list 内的路径）
