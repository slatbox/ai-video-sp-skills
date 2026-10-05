#!/usr/bin/env python3
"""提取视频尾帧（用于连贯衔接的参考素材）。

用法: tailframe.py <video> <out.png> [--offset 0.15]   # offset=距离结尾秒数
"""
import argparse
import os
import subprocess
import sys


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffprobe 失败: {r.stderr.strip()}")
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--offset", type=float, default=0.15)
    a = ap.parse_args()
    if not os.path.isfile(a.video):
        sys.exit(f"视频不存在: {a.video}")
    d = probe_duration(a.video)
    seek = max(0.0, d - a.offset)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{seek:.3f}", "-i", a.video,
         "-frames:v", "1", "-update", "1", a.out],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(a.out):
        sys.exit(f"抽帧失败:\n{r.stderr[-800:]}")
    print(a.out)


if __name__ == "__main__":
    main()
