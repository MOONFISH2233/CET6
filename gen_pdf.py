# -*- coding: utf-8 -*-
"""
把每套解析生成 PDF（精读版 + 速查版）。

做法：先生成打印专用 HTML（复用 gen_site 的渲染函数），
再用 Chrome 无头模式 --print-to-pdf 转成 PDF。

输出：
  D:\学习\六级\解析\精读版\2022年6月第1套解析（精读版）.pdf
  D:\学习\六级\解析\速查版\2022年6月第1套解析（速查版）.pdf
"""
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gen_site as G  # noqa: E402

DATA = os.path.join(HERE, "data")
BUILD = os.path.join(HERE, "pdfbuild")   # 中间 HTML
OUT = r"D:\学习\六级\解析"

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

MODULE_ORDER = G.MODULE_ORDER
MODULE_NAMES = G.MODULE_NAMES
MODULE_PARTS = G.MODULE_PARTS


# ================================================================ 页面骨架

def pdf_page(title, body, cls=""):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
/* 内联打印样式，避免 Chrome 读取外部文件时的路径问题 */
{G.PRINT_CSS}
</style>
</head>
<body class="{cls}">
<div class="wrap">
{body}
</div>
</body>
</html>
"""


# ================================================================ 精读版

def build_full(p):
    """精读版：题目 + 答案 + 逐题解析 + 逐段中译，全部展开。"""
    mods = p["modules"]
    parts = []

    # 封面
    have = [MODULE_NAMES[m] for m in MODULE_ORDER if m in mods]
    parts.append(f"""
<div class="pdf-cover">
  <div class="t">{html.escape(p["label"])} 解析</div>
  <div class="rule"></div>
  <div class="s">英语六级真题 · 精读版</div>
  <div class="m">
    含 {len(have)} 个题型：{html.escape("、".join(have))}<br>
    每题含答案、题型判定、定位句、选项逐项分析、同义替换对照<br>
    文章逐段英文 + 中译，适合精读与复盘
  </div>
</div>
""")

    # 各题型，每个另起一页
    first = True
    for m in MODULE_ORDER:
        if m not in mods:
            continue
        d = mods[m]
        brk = "" if first else "part-break"
        first = False
        parts.append(f'<div class="{brk}"></div>')
        parts.append(f'<h1 class="page">{html.escape(MODULE_PARTS[m])} · {html.escape(MODULE_NAMES[m])}</h1>')
        parts.append(f'<p class="sub">{html.escape(p["label"])}</p>')

        if m == "listening":
            parts.append(G.render_listening(d))
        elif m in ("reading1", "reading2"):
            parts.append(G.render_reading(d))
        elif m == "longreading":
            parts.append(G.render_longreading(d))
        elif m == "cloze":
            parts.append(G.render_cloze(d))
        elif m == "translation":
            parts.append(G.render_translation(d))
        elif m == "writing":
            parts.append(G.render_writing(d))

    return pdf_page(f'{p["label"]} 解析（精读版）', "".join(parts))


# ================================================================ 速查版

def build_cheat(p):
    """速查版：题目 + 答案 + 要点，无长解析，页数少。"""
    mods = p["modules"]
    parts = []

    parts.append(f"""
<div class="pdf-cover">
  <div class="t">{html.escape(p["label"])} 答案速查</div>
  <div class="rule"></div>
  <div class="s">英语六级真题 · 速查版</div>
  <div class="m">
    题目 + 答案 + 关键定位句 + 同义替换<br>
    适合做完题快速对答案、看错在哪
  </div>
</div>
""")

    # 答案汇总表（最好用的一页）
    parts.append('<h1 class="page">答案速查表</h1>')
    parts.append('<div class="card">')
    for m in MODULE_ORDER:
        if m not in mods:
            continue
        d = mods[m]
        if m == "listening":
            qs = d.get("questions", [])
            if qs:
                parts.append(f'<h2>{html.escape(MODULE_NAMES[m])}</h2>')
                parts.append(_ans_table(qs))
        elif m in ("reading1", "reading2", "cloze"):
            qs = d.get("questions", []) or []
            if m == "cloze":
                rows = d.get("rows", [])
                ans = [r.get("text", "") for r in rows if r.get("tag") == "答案"]
                if ans:
                    parts.append(f'<h2>{html.escape(MODULE_NAMES[m])}</h2>')
                    parts.append('<p class="en" style="font-size:10pt">' +
                                 " · ".join(f"{i+26}. {html.escape(a)}" for i, a in enumerate(ans)) +
                                 '</p>')
                continue
            if qs:
                parts.append(f'<h2>{html.escape(MODULE_NAMES[m])}</h2>')
                parts.append(_ans_table(qs))
        elif m == "longreading":
            sts = d.get("statements", [])
            if sts:
                items = []
                for s in sts:
                    a = s.get("analysis", {})
                    items.append(f"{s['no']}. {html.escape(a.get('para','?'))}")
                parts.append(f'<h2>{html.escape(MODULE_NAMES[m])}</h2>')
                parts.append('<p class="en" style="font-size:10pt">' + " · ".join(items) + '</p>')
    parts.append('</div>')

    # 逐题（精简）
    first = True
    for m in MODULE_ORDER:
        if m not in mods:
            continue
        d = mods[m]
        brk = "" if first else "part-break"
        first = False
        parts.append(f'<div class="{brk}"></div>')
        parts.append(f'<h1 class="page">{html.escape(MODULE_PARTS[m])} · {html.escape(MODULE_NAMES[m])}</h1>')

        if m == "listening":
            for q in d.get("questions", []):
                parts.append(_cheat_q(q))
        elif m in ("reading1", "reading2"):
            for q in d.get("questions", []):
                parts.append(_cheat_q(q))
        elif m == "longreading":
            for s in d.get("statements", []):
                parts.append(_cheat_s(s))
        elif m == "cloze":
            rows = d.get("rows", [])
            cur = None
            for r in rows:
                if r.get("tag") == "答案":
                    cur = {"ans": r.get("text", ""), "items": []}
                    parts.append(f'<div class="q"><div class="ansbadge">{html.escape(cur["ans"])}</div>')
                    parts.append('</div>')
        elif m == "translation":
            ref = d.get("reference_en", "")
            if ref:
                parts.append(f'<div class="enblock">{html.escape(ref)}</div>')
        elif m == "writing":
            sm = d.get("sample_en", "")
            if sm:
                for para in [x for x in sm.split("\n") if x.strip()]:
                    parts.append(f'<p class="en" style="margin-bottom:2mm">{html.escape(para)}</p>')

    return pdf_page(f'{p["label"]} 答案速查', "".join(parts), cls="cheat")


def _ans_table(qs):
    """答案横排：46 B · 47 A · 48 C…"""
    items = []
    for q in qs:
        a = q.get("answer", "")
        if a:
            items.append(f"{q['no']}. <b>{html.escape(a)}</b>")
    return '<p class="en" style="font-size:10.5pt;line-height:1.9">' + " &nbsp;·&nbsp; ".join(items) + '</p>'


def _cheat_q(q):
    """速查版单题：题干 + 选项 + 答案 + 定位句 + 替换对。"""
    out = ['<div class="q">']
    out.append('<div class="q-head">')
    out.append(f'<span class="q-no">{q["no"]}</span>')
    out.append('<div class="q-stem">')
    if q.get("stem"):
        out.append(f'<p class="en" style="margin:0">{html.escape(q["stem"])}</p>')
    out.append('</div></div>')

    ans = q.get("answer", "")
    if q.get("options"):
        out.append('<ul class="opts">')
        for o in q["options"]:
            cls = "correct" if o["letter"] == ans else ""
            out.append(f'<li class="{cls}"><span class="ltr">{html.escape(o["letter"])})</span>'
                       f'<span class="otxt">{html.escape(o.get("text", ""))}</span></li>')
        out.append('</ul>')

    if ans:
        out.append(f'<div class="ansbadge">{html.escape(ans)}'
                   f'<span class="qt">{html.escape(q.get("qtype", ""))}</span></div>')

    # 只保留正确项的同义替换 + 定位句
    loc = q.get("locate") or {}
    if loc.get("en"):
        out.append('<div class="locate">')
        if loc.get("para"):
            out.append(f'<span class="pn">{html.escape(loc["para"])}</span> ')
        out.append(f'<span class="en" style="font-size:9.5pt">{html.escape(loc["en"])}</span>')
        out.append('</div>')

    for o in q.get("option_analysis", []):
        if o.get("correct") and o.get("pairs"):
            out.append('<ul class="pairs">')
            for pr in o["pairs"]:
                out.append(f'<li>{html.escape(pr["orig"])} <span class="arrow">↔</span> '
                           f'{html.escape(pr["opt"])}</li>')
            out.append('</ul>')
    out.append('</div>')
    return "".join(out)


def _cheat_s(s):
    """速查版长篇阅读陈述。"""
    a = s.get("analysis", {})
    out = ['<div class="q">']
    out.append(f'<div class="q-head"><span class="q-no">{s["no"]}</span>'
               f'<div class="q-stem"><p class="en" style="margin:0">{html.escape(s.get("en",""))}</p>'
               f'</div></div>')
    if a.get("para"):
        out.append(f'<div class="ansbadge">答案：{html.escape(a["para"])} 段</div>')
    loc = a.get("定位", "")
    if loc:
        out.append(f'<div class="locate"><span class="en" style="font-size:9.5pt">{html.escape(loc[:300])}</span></div>')
    out.append('</div>')
    return "".join(out)


# ================================================================ 转 PDF

def to_pdf(html_path, pdf_path):
    """Chrome 无头模式打印成 PDF。"""
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        "file:///" + html_path.replace("\\", "/"),
    ]
    p = subprocess.run(cmd, capture_output=True, timeout=180)  # 不用 text=True，Chrome 输出是 GBK
    ok = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000
    return ok, (p.stderr or b"")[:200]


# ================================================================ 主流程

def main():
    # 拿到打印 CSS（从 gen_site 里内联）
    css_path = os.path.join(HERE, "site", "assets", "print.css")
    with open(css_path, encoding="utf-8") as f:
        G.PRINT_CSS = f.read()

    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        meta = json.load(f)

    papers = {}
    pdir = os.path.join(DATA, "paper")
    for fn in os.listdir(pdir):
        if fn.endswith(".json"):
            with open(os.path.join(pdir, fn), encoding="utf-8") as f:
                d = json.load(f)
            papers[d["set"]] = d

    os.makedirs(BUILD, exist_ok=True)
    full_dir = os.path.join(OUT, "精读版")
    cheat_dir = os.path.join(OUT, "速查版")
    os.makedirs(full_dir, exist_ok=True)
    os.makedirs(cheat_dir, exist_ok=True)

    only = sys.argv[1:] if len(sys.argv) > 1 else None
    sets = [p["set"] for p in meta["papers"]]
    if only:
        sets = [s for s in sets if s in only]

    print(f"计划生成 {len(sets)} 套 × 2 版 PDF\n", flush=True)
    ok_full = ok_cheat = fail = 0

    for i, s in enumerate(sets, 1):
        p = papers.get(s)
        if not p:
            continue
        label = p["label"].replace(" ", "")
        # 文件名对齐「原题」目录习惯
        # 文件名用可排序格式：2022-06_第1套解析（精读版）.pdf
        fnbase = f"{p['year']}-{p['month']:02d}_第{p['no']}套解析"

        # 精读版
        h1p = os.path.join(BUILD, s + "_full.html")
        with open(h1p, "w", encoding="utf-8") as f:
            f.write(build_full(p))
        pd1 = os.path.join(full_dir, fnbase + "（精读版）.pdf")
        o1, e1 = to_pdf(h1p, pd1)
        if o1:
            ok_full += 1

        # 速查版
        h2p = os.path.join(BUILD, s + "_cheat.html")
        with open(h2p, "w", encoding="utf-8") as f:
            f.write(build_cheat(p))
        pd2 = os.path.join(cheat_dir, fnbase + "（速查版）.pdf")
        o2, e2 = to_pdf(h2p, pd2)
        if o2:
            ok_cheat += 1

        sz1 = os.path.getsize(pd1) // 1024 if os.path.exists(pd1) else 0
        sz2 = os.path.getsize(pd2) // 1024 if os.path.exists(pd2) else 0
        flag = "" if (o1 and o2) else "  <<< 失败"
        print(f"[{i:>2}/{len(sets)}] {label:<16} 精读 {sz1:>5}KB  速查 {sz2:>4}KB{flag}", flush=True)
        if not (o1 and o2):
            fail += 1

    print(f"\n{'='*64}")
    print(f"精读版 {ok_full} 个 · 速查版 {ok_cheat} 个 · 失败 {fail}")
    print(f"输出目录: {OUT}")


if __name__ == "__main__":
    main()
