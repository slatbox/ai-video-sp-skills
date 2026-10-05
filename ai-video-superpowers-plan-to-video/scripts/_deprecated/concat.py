#!/usr/bin/env python3
"""按 plan.md 顺序拼接视频片段，输出成片。

用法: concat.py --project <项目根> [--out output/final.mp4] [--allow-partial]
- 读 plan.md 中 SEG 块顺序与勾选状态（默认要求全部 [x]）
- 参数一致(分辨率/fps/编码/音频) → concat 直接 copy；否则先归一化再拼
- 输出 <项目根>/<out>，打印各段与总时长
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from fractions import Fraction

SEG_HEAD = re.compile(r"^###\s*\[( |x)\]\s*(SEG-\d+)\s*$")


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"命令失败: {' '.join(cmd)}\n{r.stderr[-1200:]}")
    return r


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffprobe 失败: {path}\n{r.stderr[-500:]}")
    return json.loads(r.stdout)


def clip_info(path):
    j = probe(path)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if not v:
        sys.exit(f"无视频流: {path}")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    fr = v.get("avg_frame_rate") or v.get("r_frame_rate") or "24/1"
    try:
        fps = Fraction(fr)
    except ValueError:
        fps = Fraction(24, 1)
    return {
        "path": path, "w": v["width"], "h": v["height"], "fps": fps,
        "vcodec": v["codec_name"],
        "has_audio": a is not None,
        "sr": a.get("sample_rate") if a else None,
        "ch": a.get("channels") if a else None,
        "dur": float(j["format"].get("duration", 0)),
    }


def plan_segments(project):
    plan = os.path.join(project, "plan.md")
    if not os.path.isfile(plan):
        return None, None
    segs, cur = [], None
    for line in open(plan, encoding="utf-8"):
        m = SEG_HEAD.match(line.strip())
        if m:
            cur = {"id": m.group(2), "checked": m.group(1) == "x",
                   "dur": None, "clip": None}
            segs.append(cur)
        elif cur is not None:
            if line.startswith("###") and not SEG_HEAD.match(line.strip()):
                cur = None
            elif line.startswith("- 成片:") or line.startswith("- 成片："):
                cur["clip"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("- 时长:") or line.startswith("- 时长："):
                mm = re.search(r"(\d+)", line)
                cur["dur"] = int(mm.group(1)) if mm else None
    return plan, segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", default="output/final.mp4")
    ap.add_argument("--allow-partial", action="store_true",
                    help="允许未打钩的片段(跳过)")
    a = ap.parse_args()
    project = os.path.abspath(a.project)

    ordered = []
    plan, segs = plan_segments(project)
    if segs:
        unchecked = [s["id"] for s in segs if not s["checked"]]
        if unchecked and not a.allow_partial:
            sys.exit(f"plan 中还有未完成片段: {', '.join(unchecked)}（确认要拼接可加 --allow-partial）")
        for s in segs:
            if s["checked"] or a.allow_partial:
                ordered.append(s["clip"] or os.path.join("clips", f"{s['id']}.mp4"))
    else:
        clips_dir = os.path.join(project, "clips")
        ordered = sorted(
            os.path.join(clips_dir, f) for f in os.listdir(clips_dir)
            if re.match(r"SEG-\d+\.mp4$", f)) if os.path.isdir(clips_dir) else []
    paths = [p if os.path.isabs(p) else os.path.join(project, p) for p in ordered]
    if not paths:
        sys.exit("没有可拼接的片段")
    for p in paths:
        if not os.path.isfile(p):
            sys.exit(f"片段不存在: {p}")

    infos = [clip_info(p) for p in paths]
    for i in infos:
        print(f"  {os.path.basename(i['path'])}  {i['w']}x{i['h']}  "
              f"{float(i['fps']):.3f}fps  {i['dur']:.2f}s  "
              f"audio={'yes' if i['has_audio'] else 'no'}")

    t0 = infos[0]
    uniform = all(
        i["w"] == t0["w"] and i["h"] == t0["h"] and i["fps"] == t0["fps"]
        and i["vcodec"] == t0["vcodec"] and i["has_audio"] == t0["has_audio"]
        and i["sr"] == t0["sr"] and i["ch"] == t0["ch"] for i in infos)

    out = a.out if os.path.isabs(a.out) else os.path.join(project, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        concat_inputs = paths
        if not uniform:
            print("参数不一致 → 归一化重编码 ...")
            concat_inputs = []
            for n, i in enumerate(infos):
                tmp = os.path.join(td, f"{n:02d}.mp4")
                vf = (f"scale={t0['w']}:{t0['h']}:force_original_aspect_ratio=decrease,"
                      f"pad={t0['w']}:{t0['h']}:(ow-iw)/2:(oh-ih)/2,"
                      f"fps={float(t0['fps']):.6f},format=yuv420p")
                if i["has_audio"]:
                    cmd = ["ffmpeg", "-y", "-i", i["path"],
                           "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", tmp]
                else:
                    cmd = ["ffmpeg", "-y",
                           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                           "-i", i["path"], "-map", "1:v:0", "-map", "0:a:0", "-shortest",
                           "-vf", vf,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", tmp]
                sh(cmd)
                concat_inputs.append(tmp)
                print(f"  归一化 {os.path.basename(i['path'])} -> {tmp}")

        lst = os.path.join(td, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in concat_inputs:
                f.write("file '{}'\n".format(p.replace("'", "'\\''")))
        sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
            "-c", "copy", out])

    total = clip_info(out)["dur"]
    src_sum = sum(i["dur"] for i in infos)
    print(f"\n成片: {out}")
    print(f"总时长: {total:.2f}s (各段合计 {src_sum:.2f}s)")
    if plan and abs(total - src_sum) > 1.0:
        print("WARN 与各段合计差异 >1s，请检查")


if __name__ == "__main__":
    main()
