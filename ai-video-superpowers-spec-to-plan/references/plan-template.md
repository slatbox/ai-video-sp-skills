# 视频 Plan · <项目名称>

> 由 ai-video-superpowers-spec-to-plan 生成；plan-to-video 按此执行并打钩。状态：待审核 / 已审核
> 来源 spec：spec.md ｜ 总时长：xx s ｜ 片段数：N ｜ 画幅：16:9 ｜ 分辨率：1080P ｜ 分镜板：N 张（storyboards/）

## 默认生成参数

- model：hailuo-h3-quannengcankao（每段必带分镜板+人物参考图）
- duration：15s 固定（仅末段可 4~15s 兜底）｜ ar：<画幅> ｜ res：768P（试稿）/ 1080P（成品）

## 片段列表

### [ ] SEG-01
- 时长: 15s
- 来源场景片段: SC-xx
- 衔接: 独立（开场，无上一段）
- 分镜板: storyboards/SEG-01.png（P01–P12 黏土预演，4×3 网格）
- 分镜概览: P01 大远景… → P12 …（一行 12 节点速览，供快速审核）
- prompt: |
  @[storyboard] 是本视频的分镜蓝图——请逐镜头进行重现。……
  （references/video-prompt-template.md 模板全文填好，分镜节点 P01–P12 逐条写全）
- 参考图: @[storyboard]=storyboards/SEG-01.png, @[C1 角色名]=refs/char-a.png, @[C2 角色名]=refs/char-b.png（场景图直接写路径 refs/scene-1.png，不带 @ 标记）
- 成片: clips/SEG-01.mp4
- 备注: 台词/特殊要求（可选）

### [ ] SEG-02
- 时长: 15s
- 来源场景片段: SC-yy
- 衔接: 连贯（承接 SEG-01）← 执行时将提取 SEG-01 尾帧生成新机位首帧图，追加为本段首张参考图
- 分镜板: storyboards/SEG-02.png（P01–P12 黏土预演）
- 分镜概览: ...
- prompt: |
  ...
- 参考图: @[storyboard]=storyboards/SEG-02.png, @[C1 角色名]=refs/char-a.png, refs/scene-1.png
- 成片: clips/SEG-02.mp4

<!-- 依次 SEG-03...；最后加一行：
- [ ] 全部片段完成
 -->

## 成片

- [ ] 拼接：python3 /var/minis/skills/ai-video-superpowers-plan-to-video/scripts/concat.py --project <项目根> → output/final.mp4
