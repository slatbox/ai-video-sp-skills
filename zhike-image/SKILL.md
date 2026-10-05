---
name: zhike-image
version: 1.0.0
description: Generate images (text-to-image / image-to-image / image edit) via the 智核 platform (api.lk888.ai) with TT Image 2.5 models. Use when the user asks to generate an AI image via 智核/lk888, mentions tt-image-2.5 / tt-image-2.5-flare / tt-image-2.5-sunburst, or needs 文生图 / 图生图 / 透明背景图 / 海报图. Handles task submission, polling, and download to /var/minis/attachments/.
---

# 智核平台图片生成 (TT Image 2.5)

通过智核平台 (api.lk888.ai) 调用 TT Image 2.5 系列图像模型。支持文生图、图生图（最多 16 张参考图）、局部编辑、透明背景 PNG；比例与分辨率分开控制（1K/2K/4K，最高 3840×2160）。

## 环境

- Base URL: `https://api.lk888.ai/v1`（iSH 直连正常）
- API Key: `/var/minis/shared/zhike/image.key`（600 权限，跨会话持久）；兜底读 `/var/minis/shared/zhike/.key`（那是 zhike-video 的 key，**可能无图片模型权限**）或环境变量 `ZHIKE_API_KEY`
- 两个 key 不同：**图片用 image.key，视频用 .key**，勿混用
- HTTP 一律走 curl 子进程（iSH 内 Python urllib 有 SSL 问题）
- 脚本: `/var/minis/skills/zhike-image/scripts/image.py`
- 文档: https://akc.kk0606.com/apidoc#model/tt-image-2.5 （Vue SPA，需浏览器渲染取文本）

## 模型

| model | 说明 |
|---|---|
| `tt-image-2.5` | 主模型，按次计费 |
| `tt-image-2.5-flare` | 标准版（对应 `version: flare`），出图快、性价比高 |
| `tt-image-2.5-sunburst` | 增强版（对应 `version: sunburst`），细节足、复杂构图/文字更稳，部分渠道更贵 |

默认用 `tt-image-2.5` + `version: flare`；追求成品质量时改 `sunburst`。

## 两种协议

### A. 本站媒体协议（异步，推荐，参数最全）

1. **提交** `POST /v1/media/generate`
   ```json
   {"model": "tt-image-2.5", "prompt": "...",
    "params": {"version": "flare", "aspect_ratio": "16:9", "resolution": "1K",
               "quality": "auto", "background": "opaque", "size": "1536x864",
               "images": ["https://... 或 data:image/png;base64,..."]},
    "notify_url": "https://..."}
   ```
   - `aspect_ratio`: auto / 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3 / 5:4 / 4:5 / 2:1 / 1:2 / 21:9 / 9:21
   - `resolution`: auto / 1K（约 100 万像素）/ 2K / 4K（最高 3840×2160）
   - `quality`: auto（默认推荐）/ low / medium / high / xhigh（超高）/ max（极致）
   - `background`: opaque（默认）/ transparent（透明底 PNG，只派支持渠道）/ auto
   - `size`: 高级自定义像素尺寸（`1536x864`），**传了就忽略 aspect_ratio 和 resolution**；只接受像素写法或 auto，传 `1K`/`16:9` 会 400
   - `images`: 参考图数组 ≤16，URL 或 `data:<mime>;base64,...`（单文件解码后 ≤10MB，合计 ≤30MB，请求体 ≤50MB）
   - 联动：`aspect_ratio=auto` 时 `resolution` 自动跟随 auto，反之亦然
   - `notify_url` 是**顶层字段**，别放 params
2. **轮询** `GET /v1/media/status?task_id=...`
   - 终态看 `is_final === true`；成败看 `state`（pending/running/success/failed）；`status`/`progress` 是中文展示字段，不用于逻辑
   - 每 5~10 秒；图片通常 20 秒~2 分钟，复杂高清图 3~5 分钟；>10 分钟多为上游拥堵
   - `failed` 已自动退款
3. 成功后 `result_url` 为永久地址，直接下载。

### B. OpenAI Images 兼容（同步，一次请求直出）

`POST /v1/images/generations`，请求/响应与 OpenAI 协议一致（`model` / `prompt` / `size` / `n`），`size` 支持任意协议规则尺寸。另有 `POST /v1/images/edits`（multipart 传图或 JSON 传公网 URL）做图片编辑。
适合接入 OpenAI SDK / 现成工具，或想要简单同步调用的场景。

## 使用示例

```sh
# 提交文生图(1K 16:9 标准版)
python3 /var/minis/skills/zhike-image/scripts/image.py submit \
  --prompt "赛博朋克城市夜景..." --ar 16:9 --res 1K --version flare
# → stdout 第一行是 task_id

# 轮询到出图(打印 result_url)
python3 /var/minis/skills/zhike-image/scripts/image.py poll --task-id <ID> --timeout 600

# 下载
python3 /var/minis/skills/zhike-image/scripts/image.py download \
  --url <result_url> --output /var/minis/attachments/out.png

# 图生图(本地参考图自动转 base64 内联)
python3 .../image.py submit --prompt "改成水彩风" --image /var/minis/attachments/ref.png --res 2K

# OpenAI 兼容同步直出
python3 .../image.py openai --prompt "一只戴眼镜的橘猫" --size 1024x1024 --out /var/minis/attachments/cat.png

# 查看本 key 可用模型
python3 .../image.py models
```

## 提示词与注意

- 推荐结构:《主体 + 场景 + 风格 + 光线 + 氛围》
- 出图落到 `/var/minis/attachments/` 后用 `![desc](minis://attachments/xxx.png)` 展示给用户
- submit 失败先看响应体；图片需求给默认值：`--ar` 按内容横竖、`--res 1K` 预览 / `2K` 成品、`--version flare`
- 传了 `--size` 就别再传 `--ar`/`--res`（会被忽略）
