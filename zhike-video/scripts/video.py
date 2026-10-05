#!/usr/bin/env python3
"""智核平台(lk888.ai)视频生成 CLI —— 海螺 H3 / MiniMax-H3 系列
用法:
  video.py submit  --prompt "..." [--model hailuo-h3] [--duration 15] [--ar 16:9] [--res 768P] [--image URL...] [--video URL...] [--audio URL...] [--notify-url URL] [--raw-params '{"k":v}']
  video.py status  --task-id ID
  video.py poll    --task-id ID [--timeout 3600] [--interval 8]
  video.py download --url URL --output FILE
API Key 读取顺序: --api-key > $ZHIKE_API_KEY > /var/minis/shared/zhike/.key > /var/minis/workspace/zhike/.key(旧,兼容)
"""
import argparse, base64, json, mimetypes, os, subprocess, sys, time

BASE_URL = os.environ.get("ZHIKE_BASE_URL", "https://api.lk888.ai/v1").rstrip("/")
KEY_FILE = "/var/minis/shared/zhike/.key"
KEY_FILE_OLD = "/var/minis/workspace/zhike/.key"  # 兼容旧位置(workspace 会被清空,已迁移)


def get_key(cli_key):
    if cli_key:
        return cli_key.strip()
    if os.environ.get("ZHIKE_API_KEY"):
        return os.environ["ZHIKE_API_KEY"].strip()
    for f in (KEY_FILE, KEY_FILE_OLD):
        if os.path.exists(f):
            return open(f).read().strip()
    sys.exit("错误: 未找到 API Key。用 --api-key 传入,或设置 ZHIKE_API_KEY,或存到 " + KEY_FILE)


def http(method, path_or_url, key, body=None, timeout=60):
    url = path_or_url if path_or_url.startswith("http") else BASE_URL + path_or_url
    cmd = ["curl", "-sS", "--max-time", str(timeout), "-X", method, url,
           "-H", "Authorization: Bearer " + key, "-H", "Content-Type: application/json"]
    if body is not None:
        # 大 body(base64 内联图片)会超 argv 上限,写临时文件用 --data @file
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            tf.write(json.dumps(body, ensure_ascii=False))
            tmp = tf.name
        cmd += ["--data", "@" + tmp]
    else:
        tmp = None
    p = subprocess.run(cmd, capture_output=True, text=True)
    if tmp:
        os.unlink(tmp)
    out = p.stdout.strip()
    if p.returncode != 0:
        raise RuntimeError("curl 失败(%d): %s" % (p.returncode, p.stderr.strip()))
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError("非 JSON 响应: " + out[:500])


def as_url_or_inline(v):
    """本地文件自动转 data:base64 内联(仅图片/音频); URL/已有 data: 原样返回。视频仅支持 URL。"""
    if v.startswith(("http://", "https://", "data:")):
        return v
    if not os.path.exists(v):
        sys.exit("错误: 文件不存在且不是 URL: " + v)
    mime = mimetypes.guess_type(v)[0] or "application/octet-stream"
    with open(v, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def cmd_submit(a, key):
    params = {"duration": str(a.duration), "resolution": a.res}
    params["aspect_ratio"] = a.ar if a.ar != "adaptive" else "adaptive"
    if a.model == "hailuo-h3" and a.ar == "adaptive":
        sys.exit("错误: hailuo-h3(纯文生视频)不支持 adaptive,必须指定具体比例(如 16:9 / 9:16)")
    if a.image or a.video or a.audio:
        if a.model == "hailuo-h3" and not a.image and not a.video:
            pass  # hailuo-h3 无参考参数,交给服务端校验
        if a.image:
            params["image_url"] = [as_url_or_inline(x) for x in a.image]
        if a.video:
            params["video_url"] = [as_url_or_inline(x) for x in a.video]
        if a.audio:
            params["audio_url"] = [as_url_or_inline(x) for x in a.audio]
    if a.raw_params:
        params.update(json.loads(a.raw_params))
    if not a.image and not a.video and a.model == "hailuo-h3-quannengcankao":
        sys.exit("错误: quannengcankao(全能参考)至少需要 1 张图片或 1 个参考视频,不支持纯文字。纯文字请用 --model hailuo-h3")
    body = {"model": a.model, "prompt": a.prompt, "params": params}
    if a.notify_url:
        body["notify_url"] = a.notify_url
    r = http("POST", "/media/generate", key, body, timeout=300)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    tid = r.get("task_id") or (r.get("data") or {}).get("task_id")
    if tid is None:
        sys.exit("错误: 未返回 task_id,见上方响应")
    print("\ntask_id = %s" % tid, file=sys.stderr)


def cmd_status(a, key):
    r = http("GET", "/media/status?task_id=" + str(a.task_id), key)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r.get("state") == "success" else 1 if r.get("is_final") else 2)


def cmd_poll(a, key):
    deadline = time.time() + a.timeout
    n = 0
    while time.time() < deadline:
        try:
            r = http("GET", "/media/status?task_id=" + str(a.task_id), key)
        except RuntimeError as e:
            if n % 5 == 0:
                print("[%s] 查询失败,重试: %s" % (time.strftime("%H:%M:%S"), str(e)[:120]), flush=True)
            time.sleep(a.interval); n += 1; continue
        state, final = r.get("state"), r.get("is_final")
        if n % 5 == 0 or final:
            print("[%s] %s %s progress=%s" % (time.strftime("%H:%M:%S"), state,
                  r.get("status", ""), r.get("progress", "")), flush=True)
        if final:
            if state == "success":
                print("\nresult_url:", r.get("result_url"))
                print("cost:", r.get("cost"))
                return 0
            print("\n任务失败:", r.get("error") or r.get("status"), flush=True)
            print(json.dumps(r, ensure_ascii=False, indent=2))
            return 1
        time.sleep(a.interval)
        n += 1
    print("超时(%ds)未完成,可稍后再 poll 同一 task_id" % a.timeout)
    return 2


def cmd_download(a, key):
    cmd = ["curl", "-sSL", "--max-time", "1800", "-o", a.output, a.url]
    p = subprocess.run(cmd)
    size = os.path.getsize(a.output) if os.path.exists(a.output) else 0
    print("已下载 %s (%.1f MB)" % (a.output, size / 1e6) if p.returncode == 0 else "下载失败")
    sys.exit(p.returncode)


def main():
    ap = argparse.ArgumentParser(description="智核平台海螺H3视频生成")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("--api-key", default=None)

    s = sub.add_parser("submit")
    s.add_argument("--model", default="hailuo-h3",
                   choices=["hailuo-h3", "hailuo-h3-quannengcankao", "hailuo-h3-cankaosheng", "hailuo-h3-shouweizhen"])
    s.add_argument("--prompt", required=True)
    s.add_argument("--duration", type=int, default=10, choices=range(4, 16))
    s.add_argument("--ar", "--aspect-ratio", default="16:9",
                   choices=["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"])
    s.add_argument("--res", "--resolution", default="768P", choices=["768P", "1080P", "2K", "4K"])
    s.add_argument("--image", action="append", help="参考图片 URL/本地路径,可多次 (≤9)")
    s.add_argument("--video", action="append", help="参考视频 URL,可多次 (≤3)")
    s.add_argument("--audio", action="append", help="参考音频 URL/本地路径,可多次 (≤3)")
    s.add_argument("--notify-url", default=None)
    s.add_argument("--raw-params", default=None, help="额外 params 的 JSON,覆盖默认")

    t = sub.add_parser("status"); t.add_argument("--task-id", required=True)
    p = sub.add_parser("poll"); p.add_argument("--task-id", required=True)
    p.add_argument("--timeout", type=int, default=3600); p.add_argument("--interval", type=int, default=8)
    d = sub.add_parser("download"); d.add_argument("--url", required=True); d.add_argument("--output", required=True)

    a = ap.parse_args()
    key = get_key(a.api_key)
    {"submit": cmd_submit, "status": cmd_status, "poll": cmd_poll, "download": cmd_download}[a.cmd](a, key)


if __name__ == "__main__":
    main()
