#!/usr/bin/env python3
"""智核平台(lk888.ai)图片生成 CLI —— TT Image 2.5 系列
用法:
  image.py models
  image.py submit --prompt "..." [--model tt-image-2.5] [--version flare|sunburst]
                  [--ar 16:9] [--res 1K|2K|4K|auto] [--quality auto|low|medium|high|xhigh|max]
                  [--background opaque|transparent|auto] [--size 1536x864] [--image URL|本地路径]...
                  [--notify-url URL] [--raw-params '{"k":v}']
  image.py status --task-id ID
  image.py poll   --task-id ID [--timeout 600] [--interval 6]
  image.py download --url URL --output FILE
  image.py openai --prompt "..." [--size 1024x1024] [--n 1] [--out FILE]   # OpenAI 兼容同步端点
API Key 读取顺序: --api-key > $ZHIKE_API_KEY > /var/minis/shared/zhike/image.key > /var/minis/shared/zhike/.key
"""
import argparse, base64, json, mimetypes, os, subprocess, sys, tempfile, time

BASE_URL = os.environ.get("ZHIKE_BASE_URL", "https://api.lk888.ai/v1").rstrip("/")
KEY_FILES = [
    "/var/minis/shared/zhike/image.key",  # 本 skill 专用
    "/var/minis/shared/zhike/.key",       # zhike-video 的 key(兜底,可能无图片模型权限)
]


def get_key(cli_key):
    if cli_key:
        return cli_key.strip()
    if os.environ.get("ZHIKE_API_KEY"):
        return os.environ["ZHIKE_API_KEY"].strip()
    for f in KEY_FILES:
        if os.path.exists(f):
            k = open(f).read().strip()
            if k:
                return k
    sys.exit("错误: 未找到 API Key。用 --api-key 传入,或设置 ZHIKE_API_KEY,或存到 " + KEY_FILES[0])


def http(method, path_or_url, key, body=None, timeout=120, form=None):
    url = path_or_url if path_or_url.startswith("http") else BASE_URL + path_or_url
    cmd = ["curl", "-sS", "--max-time", str(timeout), "-X", method, url,
           "-H", "Authorization: Bearer " + key]
    tmp = None
    if form is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", "@" + form]
        tmp = form
    elif body is not None:
        # 大 body(base64 内联图)会超 argv 上限,写临时文件用 --data @file
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir="/tmp") as tf:
            tf.write(json.dumps(body, ensure_ascii=False))
            tmp = tf.name
        cmd += ["-H", "Content-Type: application/json", "--data", "@" + tmp]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if tmp and body is not None:
        os.unlink(tmp)
    out = p.stdout.strip()
    if p.returncode != 0:
        raise RuntimeError("curl 失败(%d): %s" % (p.returncode, p.stderr.strip()))
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError("非 JSON 响应(%s %s): %s" % (method, url, out[:800]))


def as_url_or_inline(v):
    """本地文件自动转 data:base64 内联; URL/已有 data: 原样返回。"""
    if v.startswith(("http://", "https://", "data:")):
        return v
    if not os.path.exists(v):
        sys.exit("错误: 文件不存在且不是 URL: " + v)
    mime = mimetypes.guess_type(v)[0] or "application/octet-stream"
    with open(v, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def cmd_models(a, key):
    r = http("GET", "/models", key)
    for m in r.get("data", []):
        print(m["id"])


def cmd_submit(a, key):
    params = {}
    if a.version:
        params["version"] = a.version
    if a.ar:
        params["aspect_ratio"] = a.ar
    if a.res:
        params["resolution"] = a.res
    if a.quality:
        params["quality"] = a.quality
    if a.background:
        params["background"] = a.background
    if a.size:
        params["size"] = a.size
    if a.image:
        params["images"] = [as_url_or_inline(x) for x in a.image]
    if a.raw_params:
        params.update(json.loads(a.raw_params))
    body = {"model": a.model, "prompt": a.prompt, "params": params}
    if a.notify_url:
        body["notify_url"] = a.notify_url  # 顶层字段
    r = http("POST", "/media/generate", key, body)
    if isinstance(r.get("data"), dict) and "task_id" in r["data"]:
        r = dict(r["data"])  # 包裹格式 {code,data:{task_id,...},msg}
    if "task_id" in r:
        print(r["task_id"])
        print(json.dumps(r, ensure_ascii=False), file=sys.stderr)
    else:
        sys.exit("提交失败: " + json.dumps(r, ensure_ascii=False))


def cmd_status(a, key):
    r = http("GET", "/media/status?task_id=%s" % a.task_id, key)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r.get("is_final") and r.get("state") != "success":
        sys.exit(1)


def cmd_poll(a, key):
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        r = http("GET", "/media/status?task_id=%s" % a.task_id, key)
        if r.get("is_final"):
            if r.get("state") == "success":
                print(r.get("result_url", ""))
                return
            sys.exit("任务失败(已自动退款): " + json.dumps(r, ensure_ascii=False))
        print("[%.0fs] %s %s %s" % (time.time() - t0, r.get("state"), r.get("status", ""),
                                    r.get("progress", "")), file=sys.stderr)
        time.sleep(a.interval)
    sys.exit("轮询超时(%ds),task_id=%s 可稍后重试" % (a.timeout, a.task_id))


def cmd_download(a, key):
    out = a.output
    p = subprocess.run(["curl", "-sSL", "--max-time", "300", "-o", out, a.url],
                       capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        sys.exit("下载失败: " + p.stderr.strip())
    print("%s (%d bytes)" % (out, os.path.getsize(out)))


def cmd_openai(a, key):
    """OpenAI 兼容同步端点 POST /v1/images/generations,一次请求直出图。"""
    body = {"model": a.model, "prompt": a.prompt, "n": a.n}
    if a.size:
        body["size"] = a.size
    if a.extra:
        body.update(json.loads(a.extra))
    r = http("POST", "/images/generations", key, body, timeout=600)
    if "error" in r:
        sys.exit("生成失败: " + json.dumps(r, ensure_ascii=False))
    data = r.get("data", [])
    if not data:
        sys.exit("无返回数据: " + json.dumps(r, ensure_ascii=False)[:800])
    for i, item in enumerate(data):
        url = item.get("url")
        b64 = item.get("b64_json")
        if a.out and (url or b64):
            if b64:
                with open(a.out, "wb") as f:
                    f.write(base64.b64decode(b64))
            else:
                subprocess.run(["curl", "-sSL", "--max-time", "300", "-o", a.out, url], check=True)
            print("%s (%d bytes)" % (a.out, os.path.getsize(a.out)))
        else:
            print(url or b64 or json.dumps(item, ensure_ascii=False))
    if r.get("usage"):
        print(json.dumps(r["usage"], ensure_ascii=False), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="智核 TT Image 2.5 图片生成 CLI")
    ap.add_argument("--api-key", help="覆盖 API Key")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("models")

    s = sub.add_parser("submit")
    s.add_argument("--prompt", required=True)
    s.add_argument("--model", default="tt-image-2.5")
    s.add_argument("--version", choices=["flare", "sunburst"], help="flare=标准版 sunburst=增强版")
    s.add_argument("--ar", help="aspect_ratio,如 16:9 / 1:1 / 9:16 / auto")
    s.add_argument("--res", help="resolution: 1K / 2K / 4K / auto")
    s.add_argument("--quality", help="auto/low/medium/high/xhigh/max")
    s.add_argument("--background", choices=["opaque", "transparent", "auto"])
    s.add_argument("--size", help="自定义像素尺寸如 1536x864(覆盖 ar/res)")
    s.add_argument("--image", action="append", help="参考图 URL 或本地路径,可多次")
    s.add_argument("--notify-url")
    s.add_argument("--raw-params", help='追加 params,如 \'{"quality":"high"}\'')

    st = sub.add_parser("status")
    st.add_argument("--task-id", required=True)

    pl = sub.add_parser("poll")
    pl.add_argument("--task-id", required=True)
    pl.add_argument("--timeout", type=int, default=600)
    pl.add_argument("--interval", type=int, default=6)

    dl = sub.add_parser("download")
    dl.add_argument("--url", required=True)
    dl.add_argument("--output", required=True)

    oa = sub.add_parser("openai")
    oa.add_argument("--prompt", required=True)
    oa.add_argument("--model", default="tt-image-2.5")
    oa.add_argument("--size", help="如 1024x1024")
    oa.add_argument("--n", type=int, default=1)
    oa.add_argument("--out", help="保存首个结果到文件")
    oa.add_argument("--extra", help='额外 body,如 \'{"quality":"high"}\'')

    a = ap.parse_args()
    key = get_key(a.api_key)
    {"models": cmd_models, "submit": cmd_submit, "status": cmd_status,
     "poll": cmd_poll, "download": cmd_download, "openai": cmd_openai}[a.cmd](a, key)


if __name__ == "__main__":
    main()
