# 视频 Plan · <项目名称>

> 由 ai-video-superpowers-spec-to-plan 生成；plan-to-video 按此执行并打钩。状态：待审核 / 已审核
> 来源 spec：spec.md ｜ 总时长：xx s ｜ 片段数：N ｜ 画幅：16:9 ｜ 分辨率：1080P

## 默认生成参数

- model：hailuo-h3（无参考图）/ hailuo-h3-quannengcankao（有参考图）
- duration：见每段（4~15 整数秒）｜ ar：16:9 ｜ res：768P（试稿）/ 1080P（成品）

## 片段列表

### [ ] SEG-01
- 时长: 12s
- 来源场景片段: SC-xx（及机位设计）
- 衔接: 独立（开场，无上一段）
- prompt: |
  <主体 + 场景/动作 + 风格 + 光线氛围 + 镜头运动；人物外观细节写全>
- 参考图: refs/char-a.png, refs/scene-1.png（无则写"无"）
- 成片: clips/SEG-01.mp4
- 备注: 台词/特殊要求（可选）

### [ ] SEG-02
- 时长: 15s
- 来源场景片段: SC-yy（及机位设计）
- 衔接: 连贯（承接 SEG-01）← 执行时将提取 SEG-01 尾帧生成新机位首帧图，作为本段参考图追加
- prompt: |
  ...
- 参考图: refs/char-a.png
- 成片: clips/SEG-02.mp4

<!-- 依次列出 SEG-03...；最后一段后加一行汇总：
- [ ] 全部片段完成
 -->

## 成片

- [ ] 拼接：python3 /var/minis/skills/ai-video-superpowers-plan-to-video/scripts/concat.py --project <项目根> → output/final.mp4
