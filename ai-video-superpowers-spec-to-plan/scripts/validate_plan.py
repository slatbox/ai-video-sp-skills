#!/usr/bin/env python3
"""校验 plan.md：SEG 块完整性、时长 4~15s（时长由内容量决定，非末段 <8s 警告）、prompt 非空、衔接字段、分镜板、参考图存在、编号连续。

v3：时长不再强制固定 15s；分镜节点只要求存在 P 序列（格数由剧情决定）。

用法: validate_plan.py <plan.md> [--project 项目根目录] [--allow-no-storyboard]
退出码: 0=通过(可有警告)  1=有错误
"""
import argparse
import os
import re
import sys

SEG_HEAD = re.compile(r"^###\s*\[( |x)\]\s*(SEG-\d+)\s*$")


def parse_segments(lines):
    segs = []
    cur = None
    for line in lines:
        m = SEG_HEAD.match(line.strip())
        if m:
            cur = {"id": m.group(2), "checked": m.group(1) == "x",
                   "raw": [], "head": line.strip()}
            segs.append(cur)
            continue
        if cur is not None:
            if line.startswith("### ") or (line.startswith("## ") and not line.startswith("###")):
                cur = None
                continue
            cur["raw"].append(line)
    return segs


def field(block, name):
    pat = re.compile(r"^-\s*" + name + r"\s*[:：]\s*(.*)$", re.M)
    m = pat.search(block)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--project", default=None)
    ap.add_argument("--allow-no-storyboard", action="store_true",
                    help="分镜板文件缺失降级为警告（分镜板待补时用）")
    args = ap.parse_args()

    plan_path = os.path.abspath(args.plan)
    project = os.path.abspath(args.project) if args.project else os.path.dirname(plan_path)
    if not os.path.isfile(plan_path):
        print(f"ERROR plan 不存在: {plan_path}")
        return 1

    with open(plan_path, encoding="utf-8") as f:
        text = f.read()

    errors, warns = [], []
    segs = parse_segments(text.splitlines())
    if not segs:
        print("ERROR 未找到任何 '### [ ] SEG-xx' 片段块（格式需与模板一致）")
        return 1

    ids = [s["id"] for s in segs]
    for i, s in enumerate(segs, 1):
        expected = f"SEG-{i:02d}"
        if s["id"] != expected:
            errors.append(f"{s['id']}: 编号不连续，期望 {expected}")

        body = "\n".join(s["raw"])
        dur = field(body, "时长")
        if not dur:
            errors.append(f"{s['id']}: 缺少 '时长' 字段")
        else:
            m = re.match(r"^(\d+)\s*s?$", dur)
            if not m:
                errors.append(f"{s['id']}: 时长格式应为 '12s'，实际 '{dur}'")
            else:
                d = int(m.group(1))
                if not (4 <= d <= 15):
                    errors.append(f"{s['id']}: 时长 {d}s 超出模型范围 4~15s")
                elif d < 8 and i < len(segs):
                    warns.append(f"{s['id']}: 时长 {d}s 偏短（非末段建议 8~15s，确认内容量确实需要）")

        prompt = field(body, "prompt")
        if not prompt or prompt.strip() in ("", "|"):
            # multi-line prompt: 'prompt: |' then indented lines
            pm = re.search(r"^-\s*prompt\s*[:：]\s*\|?\s*\n((?:\s{2,}.*\n?)+)", body, re.M)
            prompt = pm.group(1).strip() if pm else prompt
        if not prompt:
            errors.append(f"{s['id']}: prompt 为空")
        else:
            if "分镜蓝图" not in prompt:
                errors.append(f"{s['id']}: prompt 缺少分镜蓝图宣言（须基于分镜板逐镜头重现）")
            if not re.search(r"P\d{2}", prompt):
                errors.append(f"{s['id']}: prompt 缺少分镜节点 P01–Pxx")
            if "视觉风格" not in prompt:
                warns.append(f"{s['id']}: prompt 缺少'视觉风格'等模板区块，检查是否套用 video-prompt-template")
            # 台词标签检查：有中文引号台词但整段无 <d> 标签 → 警告
            if "<d>" not in prompt and re.search(r"[「“][^「」“”]{2,}[」”]", prompt):
                warns.append(f"{s['id']}: prompt 有引号台词但无 <d>[Chinese]…</d> 台词标签（影响发音稳定性，按 templates/video.txt 台词标注规则补）")

        sb = field(body, "分镜板")
        if not sb:
            errors.append(f"{s['id']}: 缺少'分镜板'字段")
        else:
            mm = re.search(r"(storyboards/[\w.\-]+\.(?:png|jpg|jpeg|webp))", sb)
            if not mm:
                errors.append(f"{s['id']}: '分镜板'字段未找到 storyboards/ 图片路径")
            else:
                p = os.path.join(project, mm.group(1))
                if not os.path.isfile(p):
                    if args.allow_no_storyboard:
                        warns.append(f"{s['id']}: 分镜板待补: {mm.group(1)}")
                    else:
                        errors.append(f"{s['id']}: 分镜板文件不存在: {mm.group(1)}（生成后重跑，或加 --allow-no-storyboard）")

        ov = field(body, "分镜概览")
        if not ov:
            warns.append(f"{s['id']}: 缺少'分镜概览'字段（建议一行 N 节点速览）")

        link = field(body, "衔接")
        if i == 1:
            if link is None:
                warns.append(f"{s['id']}: 建议标注衔接(独立/连贯)")
        else:
            if link is None:
                errors.append(f"{s['id']}: 缺少'衔接'字段(独立 或 连贯（承接 SEG-xx）)")
            elif not re.search(r"独立|连贯", link):
                errors.append(f"{s['id']}: 衔接字段须含 独立 或 连贯，实际 '{link}'")
            elif "连贯" in link and not re.search(r"SEG-\d+", link):
                errors.append(f"{s['id']}: 连贯衔接必须写明承接哪一段，如 '连贯（承接 SEG-01）'")

        refs = field(body, "参考图")
        if not refs or refs.strip() in ("无", "-", "none", "None"):
            errors.append(f"{s['id']}: 参考图为空（v2 每段必须至少带分镜板作参考图）")
        else:
            for r in re.split(r"[,，、]", refs):
                r = r.strip()
                if not r:
                    continue
                r = re.sub(r"^@\[[^\]]*\]\s*=\s*", "", r)  # @[tag]=path → path
                p = r if os.path.isabs(r) else os.path.join(project, r)
                if not os.path.isfile(p):
                    errors.append(f"{s['id']}: 参考图不存在: {r}")

        if field(body, "成片") is None:
            warns.append(f"{s['id']}: 缺少'成片'路径字段(建议 clips/{s['id']}.mp4)")

    total = 0
    for s in segs:
        d = field("\n".join(s["raw"]), "时长")
        m = re.match(r"^(\d+)", d or "")
        if m:
            total += int(m.group(1))
    sb_ok = sum(1 for s in segs
                if field("\n".join(s["raw"]), "分镜板")
                and os.path.isfile(os.path.join(project, (
                    re.search(r"storyboards/[\w.\-]+\.(?:png|jpg|jpeg|webp)",
                              field("\n".join(s["raw"]), "分镜板")).group(0)
                    if re.search(r"storyboards/[\w.\-]+\.(?:png|jpg|jpeg|webp)",
                                 field("\n".join(s["raw"]), "分镜板")) else "___"))))
    print(f"片段数: {len(segs)}  总时长: {total}s  分镜板: {sb_ok}/{len(segs)} 张就绪  项目: {project}")
    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("校验通过 ✅" if not errors else f"校验失败 ❌ ({len(errors)} 处错误)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
