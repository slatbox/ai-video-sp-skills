#!/usr/bin/env python3
"""校验 plan.md：SEG 块完整性、时长 4~15s、prompt 非空、衔接字段、参考图存在、编号连续。

用法: validate_plan.py <plan.md> [--project 项目根目录]
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

        prompt = field(body, "prompt")
        if not prompt or prompt.strip() in ("", "|"):
            # multi-line prompt: 'prompt: |' then indented lines
            pm = re.search(r"^-\s*prompt\s*[:：]\s*\|?\s*\n((?:\s{2,}.*\n?)+)", body, re.M)
            prompt = pm.group(1).strip() if pm else prompt
        if not prompt:
            errors.append(f"{s['id']}: prompt 为空")

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
        if refs and refs not in ("无", "-", "none", "None"):
            for r in re.split(r"[,，、]", refs):
                r = r.strip()
                if not r:
                    continue
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
    print(f"片段数: {len(segs)}  总时长: {total}s  项目: {project}")
    for w in warns:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("校验通过 ✅" if not errors else f"校验失败 ❌ ({len(errors)} 处错误)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
