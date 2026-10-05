---
name: zhike-video
version: 1.0.0
description: Generate videos (text-to-video, image/video/audio-reference generation) via the 智核 platform (api.lk888.ai) with MiniMax Hailuo H3 models. Use when the user asks to generate a video via 智核/lk888, mentions 海螺 H3, hailuo-h3, hailuo-h3-quannengcankao, or needs 文生视频 / 图生视频 / 参考音频生成. Handles task submission, polling, and download to /var/minis/attachments/.
---

# 智核平台视频生成 (海螺 H3 / MiniMax-H3)

通过智核平台 (api.lk888.ai) 调用 MiniMax 海螺 H3 系列视频模型。纯文生视频直出有声视频,支持 4~15 秒、768P/1080P/2K。

## 环境

- Base URL: `https://api.lk888.ai/v1`(iSH 直连正常,无需 VPN;域名 `api.lingkeai.ai` 为同站备用)
- API Key: 存于 `/var/minis/shared/zhike/.key`(600 权限;shared 目录跨会话持久),或环境变量 `ZHIKE_API_KEY`(旧位置 `/var/minis/workspace/zhike/.key` 仍兼容,但 workspace 会被清空,勿再放那里)
- HTTP 一律走 curl 子进程(iSH 内 Python urllib 有 SSL 问题)
- 脚本: `/var/minis/skills/zhike-video/scripts/video.py`

## 模型(同一 API,参数不同)

| model | 用途 | 特殊要求 |
|---|---|---|
| `hailuo-h3` | 纯文生视频 | aspect_ratio 必填**具体比例**(不支持 adaptive) |
| `hailuo-h3-quannengcankao` | 全能参考(图+视频+音频) | **至少 1 张图片或 1 个参考视频**;aspect_ratio 可 adaptive |
| `hailuo-h3-cankaosheng` | 参考生 | - |
| `hailuo-h3-shouweizhen` | 首尾帧 | - |

文档: https://akc.kk0606.com/apidoc#model/hailuo-h3 (页面为 Vue SPA,需浏览器渲染后取文本)

## API 协议

1. **创建任务** `POST /v1/media/generate`
   ```json
   {"model": "hailuo-h3", "prompt": "...",
    "params": {"duration": "15", "aspect_ratio": "16:9", "resolution": "768P",
               "image_url": ["..."], "video_url": ["..."], "audio_url": ["..."]}}
   ```
   - `duration`: "4"~"15" 字符串,按秒计费
   - `resolution`: `768P`(试稿首选) / `1080P` / `2K`(约 768P 的 1.6 倍价);quannengcankao 另支持 `4K`
   - `aspect_ratio`: 16:9 / 9:16 / 1:1 / 4:3 / 3:4 / 21:9 (+ adaptive 仅参考类)
   - image_url ≤9(前 5 张免费)、video_url ≤3(总 ≤15s,额外计费)、audio_url ≤3(免费);图片/音频可传 URL 或 `data:<mime>;base64,...` 内联(脚本对本地路径自动转内联,视频仅 URL)
   - `notify_url` 为**顶层字段**(webhook 回调,可选)
   - 鉴权: `Authorization: Bearer <key>`(也兼容 x-api-key / ?key=)
2. **轮询** `GET /v1/media/status?task_id=...`
   - 判终态用 `is_final === true`;成败用 `state`(pending/running/success/failed)
   - `status`/`progress` 是中文展示字段,不用于逻辑判断
   - 每 5~10 秒轮询;视频任务常见 5~60 分钟;failed 已自动退款
3. 成功后 `result_url` 为永久地址,直接下载。

## 使用示例

```sh
# 提交文生视频(15 秒 768P 16:9)
python3 /var/minis/skills/zhike-video/scripts/video.py submit \
  --model hailuo-h3 --prompt "赛博朋克都市夜景..." \
  --duration 15 --ar 16:9 --res 768P
# → stderr 输出 task_id

# 轮询到出片
python3 /var/minis/skills/zhike-video/scripts/video.py poll --task-id <ID> --timeout 3600

# 下载
python3 /var/minis/skills/zhike-video/scripts/video.py download --url <result_url> --output /var/minis/attachments/out.mp4
```

## 注意

- submit 失败先看响应体错误信息;长时间 pending/running(>70 分钟)多为上游拥堵,failed 自动退款
- 纯文字需求用 `hailuo-h3`;有参考图/视频/音频用 `hailuo-h3-quannengcankao`
- prompt 描述画面、主体动作与镜头运动;H3 自动生成音效
