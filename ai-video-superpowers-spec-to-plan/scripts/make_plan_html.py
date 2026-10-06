#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan.md → plan.html 审核页转换器（与 brainstorm 的 make_spec_html.py 同一排版体系）。

- markdown 转 HTML；表格自适应：≥3列→行卡片、2列→键值卡、其余可横滚
- refs/*.png 与 storyboards/SEG-xx.png 路径自动替换为可点击缩略图（storyboards 显示为"分镜板"大卡）
- 每段 SEG 卡片头部带分镜板缩略图；prompt 块折叠，点"展开 prompt"查看、一键复制
- 顶部汇总条：片段数/总时长/分镜板就绪数/衔接判定摘要

用法: python3 make_plan_html.py --project /var/minis/shared/ai-video/<slug> [--plan plan.md] [--out plan.html]
依赖: py3-markdown（apk add py3-markdown；装在 /usr/bin/python3.12，脚本自动 execv 切换）
"""
import argparse, io, os, re, sys, html as H
from html.parser import HTMLParser

try:
    import markdown
except ImportError:
    if os.path.exists('/usr/bin/python3.12'):
        os.execv('/usr/bin/python3.12', ['/usr/bin/python3.12', os.path.abspath(__file__)] + sys.argv[1:])
    raise SystemExit('需要 py3-markdown：apk add py3-markdown')

ap = argparse.ArgumentParser()
ap.add_argument('--project', required=True)
ap.add_argument('--plan', default='plan.md')
ap.add_argument('--out', default='plan.html')
a = ap.parse_args()

proj = a.project.rstrip('/')
slug = os.path.basename(proj)
s = io.open(os.path.join(proj, a.plan), encoding='utf-8').read()
MIN = 'minis://shared/ai-video/%s/' % slug

IMG_RE = r'(?:refs|storyboards|frames)/[\w.\-]+\.(?:png|jpe?g|webp)'


def thumb_img(path):
    fp = os.path.join(proj, path)
    if not os.path.exists(fp):
        print('WARN 原图缺失:', path)
        return None
    base = os.path.splitext(os.path.basename(path))[0]
    sub = path.split('/')[0]
    th = '%s/thumbs/%s.jpg' % (sub, base)
    if not os.path.exists(os.path.join(proj, th)):
        th = path
    return ('<img class="ti" loading="lazy" src="%s" data-full="%s" onclick="lb(this)">'
            '<br><code>%s</code>') % (MIN + th, MIN + path, path)


def inject_thumbs(html_str):
    def mk(m):
        img = thumb_img(m.group(0))
        return img if img else m.group(0)
    t = re.sub(r'<code>((?:refs|storyboards|frames)/[\w.\-]+\.(?:png|jpe?g|webp))</code>', r'\1', html_str)
    return re.sub(IMG_RE, mk, t)


# ---------- SEG 块解析（从 markdown 源码直接抽取，做卡片增强） ----------
SEG_HEAD = re.compile(r'^###\s*\[( |x)\]\s*(SEG-\d+)\s*$', re.M)


def seg_meta(block):
    def f(name):
        m = re.search(r'^-\s*' + name + r'\s*[:：]\s*(.*)$', block, re.M)
        return m.group(1).strip() if m else ''
    return f


def build_seg_cards():
    """每个 SEG 生成一张带头部分镜板缩略图的卡片；prompt 折叠可复制。"""
    cards = []
    matches = list(SEG_HEAD.finditer(s))
    for idx, m in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(s)
        # 回退到上一个 ## 标题或块尾
        block = s[m.start():end]
        block = re.sub(r'^##(?!#).*$', '', block, flags=re.M)  # 截掉混入的下个章节标题
        checked, segid = m.group(1) == 'x', m.group(2)
        meta = seg_meta(block)

        pm = re.search(r'^-\s*prompt\s*[:：]\s*\|?\s*\n((?:\s{2,}.*\n?)+)', block, re.M)
        prompt = '\n'.join(l.lstrip() for l in pm.group(1).rstrip().split('\n')) if pm else ''
        block_noprompt = re.sub(r'^-\s*prompt\s*[:：]\s*\|?\s*\n(?:\s{2,}.*\n?)+', '', block, flags=re.M)

        sb = re.search(r'storyboards/[\w.\-]+\.(?:png|jpe?g|webp)', meta('分镜板'))
        sb_html = ''
        if sb:
            fp = os.path.join(proj, sb.group(0))
            base = os.path.splitext(os.path.basename(sb.group(0)))[0]
            th = 'storyboards/thumbs/%s.jpg' % base
            if not os.path.exists(os.path.join(proj, th)):
                th = sb.group(0)
            if os.path.exists(fp):
                sb_html = ('<div class="sbw"><img class="sb" loading="lazy" src="%s" data-full="%s" '
                           'onclick="lb(this)" alt="分镜板 %s"><div class="sbc">分镜板 %s · 点击放大</div></div>'
                           % (MIN + th, MIN + sb.group(0), segid, segid))
            else:
                sb_html = '<div class="sbw miss">分镜板待补：%s</div>' % sb.group(0)

        md = markdown.Markdown(extensions=['tables'])
        fields_html = inject_thumbs(md.convert(block_noprompt))

        pid = 'p-%s' % segid
        cards.append(
            '<div class="seg" id="%s">'
            '<div class="seg-h"><span class="tick">%s</span><span class="sid">%s</span>%s</div>'
            '%s%s%s'
            '<div class="pwrap"><button class="pbtn" onclick="tg(this)">▸ 展开 prompt</button>'
            '<pre class="prompt" id="%s">%s</pre>'
            '<button class="cbtn" onclick="cp(\'%s\')">复制 prompt</button></div>'
            '</div>'
            % (pid, '☑' if checked else '☐', segid,
               H.escape(meta('衔接') or ''), sb_html, bl_html, fields_html, pid, H.escape(prompt), pid))
    return '\n'.join(cards)


seg_zone = ''
m0 = re.search(r'^## 片段列表\s*$', s, re.M)
if m0:
    mm1 = re.search(r'^## ', s[m0.end():], re.M)
    seg_src = s[m0.end():m0.end() + mm1.start()] if mm1 else s[m0.end():]
    header_md = seg_src.split('###', 1)[0]
    md = markdown.Markdown(extensions=['tables'])
    seg_zone = '<div class="meta">%s</div>\n%s' % (
        inject_thumbs(md.convert(header_md)).strip(), build_seg_cards())

# ---------- 其余部分按普通 markdown 转换 ----------
others = re.sub(r'^## 片段列表\s*$.*?(?=^## |\Z)', '', s, flags=re.S | re.M)
md = markdown.Markdown(extensions=['tables'])
body = md.convert(others)
body = inject_thumbs(body)

# 把"片段列表"标题插回卡片流前
body += '\n<h2>片段列表</h2>\n' + seg_zone if seg_zone else ''

CSS = """
 body{margin:0;background:#12141a;color:#e8e8ee;font:15px/1.7 -apple-system,"PingFang SC",sans-serif;padding:16px;max-width:860px}
 h1{font-size:22px;border-bottom:2px solid #2a2e3a;padding-bottom:8px}
 h2{font-size:18px;margin-top:28px;border-bottom:1px solid #2a2e3a;padding-bottom:6px}
 h3{font-size:16px;margin-top:20px}
 .meta{color:#8a90a0;font-size:13px;margin:6px 0 14px}
 .seg{background:#1b1e27;border:1px solid #2a2e3a;border-radius:12px;margin:14px 0;padding:14px 16px}
 .seg-h{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700;color:#7fb3ff;margin-bottom:10px}
 .tick{font-size:18px}
 .sid{letter-spacing:.5px}
 .sbw{margin:10px 0;text-align:center}
 .sb{width:100%;max-width:560px;border-radius:8px;cursor:zoom-in;background:#000;display:block;margin:0 auto}
 .sbc{font-size:12px;color:#8a90a0;margin-top:4px}
 .sbw.miss{border:1px dashed #3a3f4e;border-radius:8px;padding:14px;color:#8a90a0;font-size:13px}
 .seg dl,.seg p{font-size:13.5px}
 .seg ul{padding-left:18px;font-size:13.5px}
 .ti{width:132px;max-width:100%;display:block;border-radius:6px;cursor:zoom-in;background:#000;margin:2px 0}
 .pwrap{margin-top:10px;border-top:1px dashed #2a2e3a;padding-top:10px}
 .pbtn,.cbtn{background:#2a2e3a;color:#cfd6e4;border:none;border-radius:8px;padding:8px 14px;font-size:13px;margin:4px 8px 4px 0}
 .prompt{display:none;white-space:pre-wrap;word-break:break-word;background:#12141a;border:1px solid #2a2e3a;border-radius:8px;padding:12px;font-size:12.5px;line-height:1.8;color:#c9d2e3;margin:8px 0}
 .prompt.open{display:block}
 code{background:#1b1e27;padding:1px 5px;border-radius:4px;font-size:12px;color:#7fb3ff;word-break:break-all}
 pre code{background:none}
 a{color:#7fb3ff}
 hr{border:none;border-top:1px solid #2a2e3a;margin:20px 0}
 blockquote{border-left:3px solid #3a5a8a;margin:10px 0;padding:4px 12px;background:#161a24;color:#aab2c5;border-radius:0 8px 8px 0}
 .tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px 0}
 .tw table{border-collapse:collapse;font-size:13px}
 th,td{border:1px solid #2a2e3a;padding:5px 9px;text-align:left;vertical-align:top}
 th{background:#1b1e27;white-space:nowrap}
 #lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:99;flex-direction:column}
 #lb.on{display:flex}
 #lbimg{flex:1;min-height:0;overflow:auto;display:flex;align-items:center;justify-content:center}
 #lbimg img{max-width:100%;max-height:100%;transform-origin:center center;transition:transform .15s}
 #lbctl{display:flex;gap:10px;justify-content:center;padding:12px}
 #lbctl button{background:#2a2e3a;color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:16px}
"""

JS = """
function tg(btn){var p=btn.parentElement.querySelector('.prompt');
 var open=p.classList.toggle('open');
 btn.textContent=open?'▾ 收起 prompt':'▸ 展开 prompt';}
function cp(id){var t=document.getElementById(id).textContent;
 navigator.clipboard&&navigator.clipboard.writeText(t);
 var b=event.target;b.textContent='已复制 ✓';setTimeout(function(){b.textContent='复制 prompt';},1500);}
function lb(img){
 var o=document.getElementById('lb'), t=document.getElementById('lbimg').firstElementChild;
 t.src=img.getAttribute('data-full')||img.src;
 t.style.transform='scale(1)'; o.classList.add('on');}
function lbx(f){var t=document.getElementById('lbimg').firstElementChild;
 var m=t.style.transform.match(/scale\\(([\\d.]+)\\)/);var s=m?+m[1]:1;
 s=Math.min(8,Math.max(.25,s*f));t.style.transform='scale('+s+')';}
function lbcl(){document.getElementById('lb').classList.remove('on');}
"""

PAGE = ('<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width,initial-scale=1">'
 '<title>plan 审核 · %(slug)s</title><style>%(css)s</style></head><body>'
 '%(body)s'
 '<div id="lb"><div id="lbimg"><img></div><div id="lbctl">'
 '<button onclick="lbx(1.3)">＋放大</button><button onclick="lbx(0.77)">－缩小</button>'
 '<button onclick="lbcl()">关闭</button></div></div>'
 '<script>%(js)s</script></body></html>\n')

page = PAGE % dict(slug=H.escape(slug), css=CSS, js=JS, body=body)
out = os.path.join(proj, a.out)
io.open(out, 'w', encoding='utf-8').write(page)
print('已生成', out)
