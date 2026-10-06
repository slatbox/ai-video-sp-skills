---
name: ai-video-superpowers-quick
version: 1.0.0
description: AI 视频生成+剪辑套件的快速通道（quick）。当用户想快速生成一个视频片段（单段、最长 15 秒），不需要完整策划流程/审核文档时使用：访谈提问与 ai-video-superpowers-brainstorm 完全一致（一次一题、编号选项、画面风格与氛围风格分开问），参考素材收集环节也相同（素材清单逐项提问：1 自动生成 / 2 上传；人物=无头三视图+正脸特写、场景=六宫格六视图）；收集完成后不写 spec/plan/分镜板、不派审核子智能体，直接组装视频提示词（台词 <d>[Chinese]…</d> 包裹、@[tag] 参考图引用），把最终提示词+参考素材直接发给用户确认，用户同意后立即调用海螺 H3 生成并交付成片。Use when the user wants a quick single video clip (≤15s) without the full brainstorm→spec→plan pipeline.
---

# AI Video Superpowers · quick（单段快速出片）

套件**快速通道**：把 brainstorm 的访谈 + 参考素材收集压缩进来，**跳过 spec / plan / 分镜板 / 双审**，直接产出一段 ≤15s 的视频。适合"就来一个镜头/一个片段"的需求。

**边界（先讲清楚）**：
- 本技能只生成**一个视频片段，4~15 秒**。访谈中若发现剧情/台词明显撑不到 15s 内（按语速核算超载、或剧情含多场戏/多个场景转换），**不要硬塞**——提示用户改用完整流水线 `brainstorm → spec-to-plan → plan-to-video`。
- 全程**不生成** spec.md / plan.md / 分镜板 / 审核文档 / html，**不派审核子智能体**；唯一的用户确认点 = 提示词确认（第 3 步）。

## 项目目录约定

```
/var/minis/shared/ai-video-quick/<slug>/
├── refs/        # 参考图（人物/场景/物品/风格，用户审核通过后落盘）
└── output/      # 成片 quick.mp4
```

- slug 用小写英文/拼音（如 `coffee-ad`）。prompt 全文留档一份 `<slug>/prompt.md`（**仅复跑留档，非审核文档**）。
- 同名项目已存在时先问用户：重做还是迭代。

## 第 1 步 · 访谈（与 brainstorm 完全一致）

提问流程、形式与 `ai-video-superpowers-brainstorm/SKILL.md` 的「访谈流程」**完全相同**，逐条遵守：

1. **一次只问一个问题**，等回答后再问下一个；用户已提到的信息不要重复问。
2. 每题给 2~4 个**推荐选项 + 自定义**，数字编号（1. / 2. / 3. …），用户可直接回复数字。
3. 按重要性依次覆盖：
   - 用途/投放平台
   - **目标时长**：本技能单段 4~15s，按"台词秒数 + 动作余量"给推荐值（核算规则见第 3 步）；用户想法明显 >15s → 当场提示走完整流水线
   - 画幅比例（16:9 / 9:16 / 1:1 …）
   - **画面风格**（写实/动漫/3D/水墨…）——选定后**再单独问氛围风格**（阴郁/温馨/热血…），两者分开问分开记，勿合并
   - 人物（数量、身份、外貌：年龄/发型/服装/气质）
   - 场景（地点、时代、时间光线，要具体）
   - 剧情梗概与节奏、台词/旁白（**逐句写出具体台词**，不要"两人对话"式概括）
   - 配乐音效偏好、分辨率（768P 试稿 / 1080P 成品）
4. 某项用户说"都行"时，**替他定默认值并说明理由**，不要僵持。
5. 文字收齐后进入第 2 步参考素材收集。

## 第 2 步 · 参考素材收集（与 brainstorm 完全一致）

1. 先从文字信息整理**素材清单**（每个出场人物 / 每个场景 / 每个关键物品 / 可选全局风格图），在 chat 里列出让用户过目。
2. **逐项单独提问**，一项一题，格式固定：

   > 「<设定名>」（<一句话说明>）的参考图素材怎么来？
   > 1. 自动生成（我按规则写提示词生成，生成后给你审核）
   > 2. 上传已有素材（你直接发图给我）

3. **选 2（上传）**：图落在 `/var/minis/attachments/`，复制进项目 `refs/` 并命名（`refs/char-xxx.png`、`refs/scene-xxx.png`、`refs/prop-xxx.png`）。上传图**不强制**符合生成规格（自有素材原样用），明显不利时提醒一致性风险。
4. **选 1（自动生成）**：
   ```sh
   python3 /var/minis/skills/zhike-image/scripts/image.py submit \
     --prompt "..." --ar 16:9 --res 1K --version flare
   # task_id 落盘防丢；poll --task-id <ID> --timeout 600；download 到 refs/
   ```
   （协议先读 `/var/minis/skills/zhike-image/SKILL.md`；图片 key `/var/minis/shared/zhike/image.key`；下载直接落 `/var/minis/shared/`，勿落 workspace/attachments。）
   - **人物图**：无头全身三视图 + 正脸特写、横版 2K 纯白背景（`--ar 16:9 --res 2K`）。提示词模板与实战范例**照读并遵守** `/var/minis/skills/ai-video-superpowers-brainstorm/references/char-ref-prompt.md`。
   - **场景图**：单张 3×2 六宫格六视图（①45°俯视全景 ②90°垂直俯视 ③正视图 ④反视图 ⑤左视图 ⑥右视图，元素跨视图一致、纯场景无人物无文字），`--ar 16:9 --res 2K`。提示词写法同 brainstorm SKILL.md「场景/环境参考图」段。
   - **物品图**：白底单物特写，多角度可选。
5. **展示审核**：用 minis:// 预览链接给用户看，**通过才落盘 refs/**；不通过改提示词重生成（最多 2~3 轮，仍不满意记"暂缺"照常继续）。

## 第 3 步 · 直接生成提示词 → 发用户确认（核心步骤）

素材收齐后，**不写 spec/plan，直接组装视频提示词**：

1. **组装模板**：读取 `references/video-prompt.md`，**照抄其全部段落**（视觉风格/动作语言/视觉特效/摄影风格/音频/环境/情感基调/节奏与递进/动作节点/台词标注规则），方括号占位逐项替换。**不得漏段**——漏段会导致模型表现失控。
2. **动作节点 P01~Pxx**：没有分镜板，但 H3 依赖动作节点理解节奏。按剧情写 **2~6 个 P 节点**（每节点=机位/景别/人物位置/核心动作/画面细节一句话），总节拍量与时长匹配，不写满、不超载。
3. **台词格式（硬性）**：所有发声台词（对白+旁白）写成 `<d>[Chinese]台词原文</d>`——一句一标签、长句按节奏拆分、标签内只放台词原文（不加说话人名/动作描述）；内心独白/环境音不打标签。
4. **参考图引用格式**：prompt 中用 `@[标签]` 引用素材（`@[char1]`/`@[scene1]`/`@[prop1]`/`@[style]`），**标签出现顺序 = 提交时 `--image` 传入顺序**，一一对应。首个节点段写明"@[char1] 是 C1 最终外观的唯一依据"式声明（模板已含句式，照用）。
5. **时长核算（宁松勿密）**：对白 3~3.5 字/秒、旁白 3.5~4 字/秒（含 ~0.3s 句间停顿），台词总秒数 + 15~25% 动作余量 = 建议 duration（4~15 取整）。算出来 >15s → 删台词/精简剧情，或建议走完整流水线；明显 <4s → 建议 duration=4~5。
6. **发给用户确认（本技能唯一确认点）**，在 chat 里直接给出：
   - **最终提示词全文**（代码块，可直接复制）
   - **参考素材清单**：每张图 minis:// 预览 + 对应 `@[标签]`
   - 生成参数：duration / 画幅 / 分辨率 / 模型（有参考图→`hailuo-h3-quannengcankao`，纯文生→`hailuo-h3`）
   - 一句话剧情摘要
   明确问："按这份提示词生成？（回复确认或提出修改）"。**用户未确认不提交**。修改则改完再发。

7. 用户确认后把 prompt 全文落档 `<slug>/prompt.md`（头部注明日期/参数，仅留档）。

## 第 4 步 · 生成视频并交付

1. **提交**（细节先读 `/var/minis/skills/zhike-video/SKILL.md`；视频 key `/var/minis/shared/zhike/.key`；HTTP 一律走脚本，勿用 urllib）：
   ```sh
   python3 /var/minis/skills/zhike-video/scripts/video.py submit \
     --model <hailuo-h3-quannengcankao | hailuo-h3> \
     --prompt "<确认后的提示词全文>" \
     --duration <4~15> --ar <画幅> --res <768P|1080P> \
     --image refs/xxx.png --image refs/yyy.png   # 顺序与 @[tag] 一一对应
   ```
   task_id 在 **stdout 首行**（`task_id = 123`），立即记下。
2. **轮询**：`poll --task-id <ID> --timeout 780`，用 shell_execute 的 `delay`/timeout 链反复跑到 `is_final`（常见 5~60 分钟）；>70 分钟 pending 视为上游拥堵，告知用户。期间向用户简报状态，不要空转。
3. **下载交付**：`download --url <result_url> --output /var/minis/shared/ai-video-quick/<slug>/output/quick.mp4`；ffprobe 核对时长与设定差 ≤1s。
4. **交付**：给用户 `[quick.mp4](minis://shared/ai-video-quick/<slug>/output/quick.mp4)` 链接 + 一句参数摘要。**无审核环节**，直接结束；提示可用 `ffmpeg-skill` 精修（字幕/配乐/裁剪/调色）。

## 失败与重试

- `state=failed`（已自动退款）：重试 1 次（微调 prompt/精简节点）；再失败把错误告知用户，问继续还是调整。
- submit 偶发空输出/TLS 瞬断：sleep 几秒重试即可。
- 成片明显异常（黑屏/时长异常）：重试一次，仍异常报告用户决定。

minis_url: minis://shared/ai-video-sp-skills/ai-video-superpowers-quick/SKILL.md
