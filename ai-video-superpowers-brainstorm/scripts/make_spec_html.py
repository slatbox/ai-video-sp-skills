#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spec.md → spec.html 审核页转换器。

spec.md 保持纯文本（供 skill/子智能体读取）；本脚本生成给人看的 HTML：
- markdown 转 HTML（标题/列表/引用等）
- 表格自适应布局：>4 列 → 卡片式（每行一卡，字段竖排）；2 列 → 均衡键值卡（值换行）；其余 → 可横滚表格
- 单元格里的 refs/*.png 参考图路径自动替换为可点击缩略图（放大看原图）
- 第 8 节参考素材注入缩略图卡片（点击放大原图，＋/－缩放，懒加载）
- 缩略图来源 refs/thumbs/<name>.jpg（不存在则用原图）

用法: python3 make_spec_html.py --project /var/minis/shared/ai-video/<slug>
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
ap.add_argument('--spec', default='spec.md')
ap.add_argument('--out', default='spec.html')
a = ap.parse_args()

proj = a.project.rstrip('/')
slug = os.path.basename(proj)
s = io.open(os.path.join(proj, a.spec), encoding='utf-8').read()
MIN = 'minis://shared/ai-video/%s/' % slug

# ---------- 表格解析器 ----------
class TP(HTMLParser):
    def __init__(self, html_str):
        super().__init__()
        self.rows = []
        self._cur = self._cell = None
        self.feed(html_str)

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self._cur = []
        elif tag in ('td', 'th'):
            self._cell = []

    def handle_endtag(self, tag):
        if tag == 'tr' and self._cur is not None:
            if self._cur:
                self.rows.append(self._cur)
            self._cur = None
        elif tag in ('td', 'th') and self._cell is not None:
            self._cur.append(''.join(self._cell).strip())
            self._cell = None

    def handle_data(self, d):
        if self._cell is not None:
            self._cell.append(d)

    def handle_entityref(self, name):
        if self._cell is not None:
            self._cell.append('&%s;' % name)

    def handle_charref(self, name):
        if self._cell is not None:
            self._cell.append('&#%s;' % name)


def table_to_rowcards(tbl_html):
    """宽表 → 卡片列表。返回卡片 HTML 或 None。"""
    rows = TP(tbl_html).rows
    if not rows or len(rows) < 2:
        return None
    header = rows[0]
    ncol = len(header)
    cards = []
    for r in rows[1:]:
        if not r or all(not c for c in r):
            continue
        if ncol >= 6 and len(r) >= 2:
            title = (r[0] + ' · ' + r[1]).strip(' ·')
            fields = list(zip(header[2:], r[2:]))
        else:
            title = r[0]
            fields = list(zip(header[1:], r[1:]))
        dl = []
        for k, v in fields:
            if not k and not v:
                continue
            vh = H.escape(v) if v else '—'
            vh = re.sub(r'refs/[A-Za-z0-9\-]+\.png', lambda mm: thumb_img(mm.group(0)) or mm.group(0), vh)
            dl.append('<dt>%s</dt><dd>%s</dd>' % (H.escape(k), vh))
        cards.append('<div class="rc"><div class="rc-h">%s</div><dl>%s</dl></div>'
                     % (H.escape(title), ''.join(dl)))
    return '\n'.join(cards) if cards else None


def table_to_kv(tbl_html):
    """两列键值表 → 均衡键值卡（dt 较窄、dd 占余宽自动换行）。"""
    rows = TP(tbl_html).rows
    if not rows or len(rows) < 2:
        return None
    dl = []
    for r in rows[1:]:  # 跳过表头（项/值）
        if len(r) >= 2 and (r[0] or r[1]):
            dl.append('<dt>%s</dt><dd>%s</dd>' % (H.escape(r[0]), H.escape(r[1]) if r[1] else '—'))
    return '<div class="kv"><dl>%s</dl></div>' % ''.join(dl) if dl else None


def thumb_img(path):
    """refs/x.png → 缩略图 img HTML（含 data-full 原图）；文件不存在返回 None。"""
    if not path.startswith('refs/'):
        return None
    fp = os.path.join(proj, path)
    if not os.path.exists(fp):
        print('WARN 原图缺失:', path)
        return None
    base = os.path.splitext(os.path.basename(path))[0]
    th = 'refs/thumbs/%s.jpg' % base
    if not os.path.exists(os.path.join(proj, th)):
        th = path
    return ('<img class="ti" loading="lazy" src="%s" data-full="%s" onclick="lb(this)">'
            '<br><code>%s</code>') % (MIN + th, MIN + path, path)


def inject_thumbs(tbl_html):
    """把表格单元格里的 refs/*.png（含 <code> 包裹）替换为可点击缩略图。"""
    t = re.sub(r'<code>(refs/[A-Za-z0-9\-]+\.png)</code>', r'\1', tbl_html)

    def mk(m):
        img = thumb_img(m.group(0))
        return img if img else m.group(0)

    return re.sub(r'refs/[A-Za-z0-9\-]+\.png', mk, t)


def process_tables(html):
    def repl(m):
        tbl = m.group(0)
        head_zone = tbl[:tbl.index('</tr>')] if '</tr>' in tbl else tbl
        ncol = len(re.findall(r'<th[ >]', head_zone))
        if ncol >= 3:
            cards = table_to_rowcards(tbl)
            if cards:
                return cards
        elif ncol == 2:
            kv = table_to_kv(tbl)
            if kv:
                return kv
        return '<div class="tw">' + inject_thumbs(tbl) + '</div>'
    return re.sub(r'<table>.*?</table>', repl, html, flags=re.S)

# ---------- markdown → html ----------
m8 = re.search(r'^(## 8\..*?)^## 9\.', s, re.S | re.M)
if m8:
    before, sec8, after = s[:m8.start(1)], m8.group(1), s[m8.end():]
else:
    before, sec8, after = s, '', ''

md = markdown.Markdown(extensions=['tables'])
body = process_tables(md.convert(before))
if after.strip():
    md.reset()
    body += '\n' + process_tables(md.convert(after))

# ---------- 第 8 节 → 素材卡片 ----------
if m8:
    cards = []
    for mm in re.finditer(r'^###\s*\d+\.\s*(.+?)\s*$\s*\n-\s*路径：`([^`]+)`(.*?)$', sec8, re.M):
        name, path, rest = mm.group(1).strip(), mm.group(2).strip(), mm.group(3)
        mu = re.search(r'用途：([^|｜\n]+)', rest)
        use = mu.group(1).strip() if mu else ''
        base = os.path.splitext(os.path.basename(path))[0]
        thumb = 'refs/thumbs/%s.jpg' % base
        if not os.path.exists(os.path.join(proj, thumb)):
            thumb = path
        if not os.path.exists(os.path.join(proj, path)):
            print('WARN 原图缺失:', path)
        cards.append((name, path, use, thumb))
    parts = ['<h2>8. 参考素材 · 审核视图（点击图片放大）</h2>',
             '<div class="meta">共 %d 张 · 点击放大（＋/－缩放）· 原图路径见卡片</div>' % len(cards),
             '<div class="grid">']
    for name, path, use, thumb in cards:
        parts.append(
            '<figure class="card"><img src="' + MIN + H.escape(thumb) + '" data-full="' + MIN + H.escape(path) +
            '" alt="' + H.escape(name) + '" loading="lazy" onclick="lb(this)">'
            '<figcaption><b>' + H.escape(name) + '</b>'
            '<span class="u">' + H.escape(use) + '</span>'
            '<code>' + H.escape(path) + '</code></figcaption></figure>')
    parts.append('</div>')
    body += '\n' + '\n'.join(parts)

CSS = """
 body{margin:0;background:#12141a;color:#e8e8ee;font:15px/1.7 -apple-system,"PingFang SC",sans-serif;padding:16px;max-width:860px}
 h1{font-size:22px;border-bottom:2px solid #2a2e3a;padding-bottom:8px}
 h2{font-size:18px;margin-top:28px;border-bottom:1px solid #2a2e3a;padding-bottom:6px}
 h3{font-size:16px;margin-top:20px}
 .tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px 0}
 .tw table{border-collapse:collapse;font-size:13px}
 th,td{border:1px solid #2a2e3a;padding:5px 9px;text-align:left;vertical-align:top}
 th{background:#1b1e27;white-space:nowrap}
 tr:nth-child(even) td{background:#171921}
 .rc{background:#1b1e27;border:1px solid #2a2e3a;border-radius:10px;margin:10px 0;padding:12px 14px}
 .rc-h{font-weight:700;color:#7fb3ff;margin-bottom:8px;font-size:15px;border-bottom:1px dashed #2a2e3a;padding-bottom:6px}
 .rc dl{display:grid;grid-template-columns:minmax(84px,26%) 1fr;gap:8px 14px;margin:0;font-size:13px}
 .rc dt{color:#8a90a0;margin:0;flex-shrink:0}
 .rc dd{margin:0;color:#d8dce6;word-break:break-word}
 .kv{background:#1b1e27;border:1px solid #2a2e3a;border-radius:10px;margin:10px 0;padding:14px 16px}
 .kv dl{display:grid;grid-template-columns:minmax(84px,30%) 1fr;gap:9px 16px;margin:0;font-size:13.5px}
 .kv dt{color:#9aa2b2;font-weight:600;margin:0}
 .kv dd{margin:0;color:#d8dce6;word-break:break-word}
 .ti{width:132px;max-width:100%;display:block;border-radius:6px;cursor:zoom-in;background:#000;margin:2px 0}
 blockquote{border-left:3px solid #3a5a8a;margin:10px 0;padding:4px 12px;background:#161a24;color:#aab2c5;border-radius:0 8px 8px 0}
 code{background:#1b1e27;padding:1px 5px;border-radius:4px;font-size:12px;color:#7fb3ff;word-break:break-all}
 pre{background:#1b1e27;padding:10px;border-radius:8px;overflow:auto}
 pre code{background:none}
 a{color:#7fb3ff}
 hr{border:none;border-top:1px solid #2a2e3a;margin:20px 0}
 .meta{color:#8a90a0;font-size:13px;margin:6px 0 14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
 .card{margin:0;background:#1b1e27;border-radius:10px;overflow:hidden;border:1px solid #2a2e3a}
 .card img{width:100%;display:block;background:#000;cursor:zoom-in}
 .card figcaption{padding:8px 10px;font-size:12px;display:flex;flex-direction:column;gap:3px}
 .card .u{color:#8a90a0}
 #lb{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:99;flex-direction:column}
 #lb.on{display:flex}
 #lbimg{flex:1;min-height:0;overflow:auto;display:flex;align-items:center;justify-content:center}
 #lbimg img{max-width:100%;max-height:100%;transform-origin:center center;transition:transform .15s}
 #lbctl{display:flex;gap:10px;justify-content:center;padding:12px}
 #lbctl button{background:#2a2e3a;color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:16px}
"""

JS = """
function lb(img){
 var o=document.getElementById('lb'), t=document.getElementById('lbimg').firstElementChild;
 t.src=img.getAttribute('data-full')||img.src;
 t.style.transform='scale(1)'; o.classList.add('on');
}
function lbx(f){var t=document.getElementById('lbimg').firstElementChild;
 var m=t.style.transform.match(/scale\\(([\\d.]+)\\)/);var s=m?+m[1]:1;
 s=Math.min(8,Math.max(.25,s*f));t.style.transform='scale('+s+')';}
function lbcl(){document.getElementById('lb').classList.remove('on');}
"""

PAGE = ('<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width,initial-scale=1">'
 '<title>spec 审核 · %(slug)s</title><style>%(css)s</style></head><body>'
 '%(body)s'
 '<div id="lb"><div id="lbimg"><img></div><div id="lbctl">'
 '<button onclick="lbx(1.3)">＋放大</button><button onclick="lbx(0.77)">－缩小</button>'
 '<button onclick="lbcl()">关闭</button></div></div>'
 '<script>%(js)s</script></body></html>\n')

page = PAGE % dict(slug=H.escape(slug), css=CSS, js=JS, body=body)
out = os.path.join(proj, a.out)
io.open(out, 'w', encoding='utf-8').write(page)
print('已生成', out)
