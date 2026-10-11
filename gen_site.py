# -*- coding: utf-8 -*-
"""
把 data/ 下的 JSON 渲染成静态网站。

输出到 site/：
  index.html                 首页：考期列表 + 套卷入口 + 专项入口
  p/<set>.html               套卷页：7 个模块的入口 + 概览
  p/<set>/<module>.html      模块页：该模块的完整内容
  section/<module>.html      专项页：某题型跨全部套次
  assets/style.css
  assets/app.js

设计依据：建议.txt 里的「四步走」学习法
  1. 按方法做题  2. 核实对错  3. 精读全文  4. 在句子中背单词
页面因此提供：折叠答案（先自己做）、中英对照开关、逐题解析、逐段翻译。
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SITE = os.path.join(HERE, "site")

MODULE_ORDER = ["writing", "listening", "cloze", "longreading",
                "reading1", "reading2", "translation"]

MODULE_NAMES = {
    "writing": "写作", "listening": "听力", "cloze": "选词填空",
    "longreading": "长篇阅读", "reading1": "仔细阅读①",
    "reading2": "仔细阅读②", "translation": "翻译",
}

MODULE_PARTS = {
    "writing": "Part I", "listening": "Part II",
    "cloze": "Part III A", "longreading": "Part III B",
    "reading1": "Part III C1", "reading2": "Part III C2",
    "translation": "Part IV",
}

# 只有这几个题型的源页带「真题高频词」表；写作/翻译恒为空
HFW_MODULES = ("listening", "cloze", "longreading", "reading1", "reading2")

# 题型图标（24×24 线性图标，stroke 用 currentColor，跟着主题变色）
MODULE_ICONS = {
    "writing": '<path d="M4 20h4L20 8a2.8 2.8 0 0 0-4-4L4 16v4z"/><path d="M14 6l4 4"/>',
    "listening": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="2"/>'
                 '<rect x="17" y="14" width="4" height="6" rx="2"/>',
    "cloze": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M8 10h8M8 14h4"/>',
    "longreading": '<path d="M4 6h16M4 10h16M4 14h10M4 18h6"/>',
    "reading1": '<path d="M12 7c-2-1.5-5-2-8-2v13c3 0 6 .5 8 2 2-1.5 5-2 8-2V5c-3 0-6 .5-8 2z"/>'
                '<path d="M12 7v13"/>',
    "reading2": '<path d="M12 7c-2-1.5-5-2-8-2v13c3 0 6 .5 8 2 2-1.5 5-2 8-2V5c-3 0-6 .5-8 2z"/>'
                '<path d="M12 7v13"/><path d="M7 9h2M7 12h2"/>',
    "translation": '<path d="M4 6h9M8 6c0 5-1.5 8-4 10"/><path d="M6 12c1.5 3 4 5 6 5.5"/>'
                   '<path d="M13 20l4-9 4 9"/><path d="M14.5 17h5"/>',
}


def icon(m, cls="ico"):
    """题型小图标；没有对应图标就返回空串（不影响原有布局）。"""
    p = MODULE_ICONS.get(m)
    if not p:
        return ""
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{p}</svg>')


def esc(s):
    return html.escape(str(s or ""), quote=True)


def rel(depth):
    return "../" * depth if depth else ""


# ================================================================ 页面骨架

def page(title, body, depth=0, subtitle="", extra_head="", body_class="",
         extra_js=""):
    r = rel(depth)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<meta name="description" content="{esc(subtitle or title)}">
<link rel="stylesheet" href="{r}assets/style.css">
<link rel="icon" href="{r}assets/img/favicon.png">
<link rel="apple-touch-icon" href="{r}assets/img/logo.png">
{extra_head}
</head>
<body class="{body_class}">
<header class="site">
  <div class="site-inner">
    <a class="brand" href="{r}index.html"><img class="logo" src="{r}assets/img/logo.png" alt="">六级真题精读</a>
    <a class="tools" style="margin:0" href="{r}hfw.html">重点词</a>
    <a class="tools" style="margin:0" href="{r}me.html">我的学习<span class="vcount" id="vocabCount">0</span></a>
    <button class="tools" style="margin:0" onclick="toggleTheme()" aria-label="切换主题" id="themeBtn">◐</button>
  </div>
</header>
<div class="wrap" id="top">
{body}
<footer class="site">
  <p>真题与解析整理自公开资料，仅供个人学习使用。内容版权归原权利人所有。</p>
  <p>页面上的台词与图片版权归原作者／版权方所有，仅作个人学习非商业使用，侵删。</p>
  <p>共 {TOTAL_SETS} 套 · {TOTAL_MODULES} 个题型模块 · 覆盖 2022 年 6 月 — 2026 年 6 月</p>
</footer>
</div>
<script src="{r}assets/app.js"></script>
<script src="{r}assets/word.js"></script>
<script src="{r}assets/quotes.js"></script>
<script src="{r}assets/quiz.js"></script>
{extra_js}
</body>
</html>
"""


# ================================================================ 通用组件

def crumb(items, depth):
    """面包屑 items = [(文字, href或None), ...]"""
    r = rel(depth)
    parts = []
    for i, (txt, href) in enumerate(items):
        if href is None:
            parts.append(esc(txt))
        else:
            parts.append(f'<a href="{r}{href}">{esc(txt)}</a>')
    return '<div class="crumb">' + " / ".join(parts) + "</div>"


def tools_bar(with_answer_toggle=True):
    btns = [
        '<button onclick="toggleZh()" id="zhBtn">中文对照</button>',
        '<button onclick="toggleTheme()" id="themeBtn2">深色</button>',
    ]
    if with_answer_toggle:
        btns.insert(0, '<button onclick="toggleAns()" id="ansBtn">显示答案</button>')
    return '<div class="tools">' + "".join(btns) + "</div>"


ANSHINT = ('<div class="anshint">答案已隐藏 —— 先自己做一遍，再点上方'
           '「显示答案」核实对错。<br>快捷键：A 切换答案 · Z 切换中文 · D 切换主题</div>')


# ================================================================ 首页

def build_index(meta):
    papers = {p["set"]: p for p in meta["papers"]}

    # 专项入口
    counts = {}
    for p in meta["papers"]:
        for m in p["modules"]:
            counts[m] = counts.get(m, 0) + 1

    quick = ['<div class="quick">']
    for m in MODULE_ORDER:
        n = counts.get(m, 0)
        if not n:
            continue
        quick.append(
            f'<a href="section/{m}.html"><span class="k">{icon(m)}{MODULE_NAMES[m]}</span>'
            f'<span class="v">{n} 套可练 · 横向刷历年</span></a>'
        )
    quick.append('</div>')

    # 按考期列出套卷
    periods_html = []
    for per in meta["periods"]:
        pk = per["period"]
        y, mo = pk.split("-")
        label = f"{y} 年 {int(mo)} 月"
        rows = ['<div class="setlist">']
        for s in per["sets"]:
            p = papers.get(s)
            if not p:
                continue
            chips = []
            for m in MODULE_ORDER:
                if m in p["modules"]:
                    chips.append(f'<span class="mchip">{MODULE_NAMES[m]}</span>')
                else:
                    chips.append(f'<span class="mchip off">{MODULE_NAMES[m]}</span>')
            rows.append(
                f'<a class="setrow" href="p/{s}.html">'
                f'<span class="lbl">第 {p["no"]} 套</span>'
                f'<span class="mods">{"".join(chips)}</span></a>'
            )
        rows.append("</div>")
        periods_html.append(
            f'<div class="period"><div class="period-head">'
            f'<span>{esc(label)}</span><span class="n">{len(per["sets"])} 套</span></div>'
            + "".join(rows) + "</div>"
        )

    body = f"""
<div class="hero hero-art">
  <h1>六级真题精读</h1>
  <p>2022 年 6 月 — 2026 年 6 月，共 {meta['total_sets']} 套真题。</p>
  <p>每套含听力原文与逐句中译、阅读逐段翻译、逐题解析、翻译参考译文与写作范文。</p>
</div>

<div class="qcard" data-quote="daily">
  <div class="qhead"><span class="qtag">每日一句</span><button class="qbtn" type="button">换一句</button></div>
</div>


<div class="card" style="border:2px solid var(--accent)">
  <h2><span class="tag">计划</span>62 天备考打卡</h2>
  <p style="font-size:14px;color:var(--fg-soft);margin:0 0 10px">
    按《建议.txt》排好的 62 天日程（10/11 起，12/12 考试）：阶段一只做阅读 + 听力，阶段二加写作翻译，阶段三整套模考。
    每天点开就知道该做哪一篇、走到第几步，勾选进度存在本机。
  </p>
  <a class="setrow" href="plan/index.html" style="border-color:var(--accent)">
    <span class="lbl">打开打卡站<br><span style="font-size:12px;color:var(--fg-faint)">倒计时 · 今日任务 · 进度条</span></span>
    <span class="mods" style="justify-content:flex-end">
      <span style="font-size:13px">→ 我要按计划走</span>
    </span>
  </a>
</div>

{"".join(quick)}

<div class="card">
  <h2><span class="tag">怎么用</span>四步走</h2>
  <div class="steps">
    <span class="st on">1 做题</span>
    <span class="st on">2 核实对错</span>
    <span class="st on">3 精读全文</span>
    <span class="st on">4 句子中背单词</span>
  </div>
  <p style="font-size:14px;color:var(--fg-soft);margin:0">
    进任意一篇解析：先点「隐藏答案」自己做一遍 → 再点「显示答案」核实对错，
    看每题<strong>为什么错</strong> → 然后逐段精读，生词查出来写在旁边 →
    最后回头读那些生词所在的句子，在句子里记单词。
  </p>
</div>

<h2 style="font-size:16px;margin:26px 0 6px">按考期浏览</h2>
<p class="sub" style="margin-bottom:0">划掉的表示源站未收录该题型解析。</p>
{"".join(periods_html)}
"""
    return page("六级真题精读 · 2022–2026 历年真题与解析", body, 0,
                "大学英语六级历年真题、听力原文、逐题解析、翻译参考译文与写作范文")


# ================================================================ 套卷页

def build_paper(p, meta):
    s = p["set"]
    mods = p["modules"]
    cards = []

    for m in MODULE_ORDER:
        name = MODULE_NAMES[m]
        part = MODULE_PARTS[m]
        if m in mods:
            d = mods[m]
            desc = module_desc(m, d)
            cards.append(
                f'<a class="setrow" href="{s}/{m}.html" style="margin-bottom:8px">'
                f'<span class="lbl">{esc(part)}<br>{esc(name)}</span>'
                f'<span class="mods" style="justify-content:flex-start;text-align:left">'
                f'<span style="font-size:12.5px;color:var(--fg-faint)">{esc(desc)}</span>'
                f'</span></a>'
            )
        else:
            cards.append(
                f'<div class="setrow" style="opacity:.5">'
                f'<span class="lbl">{esc(part)}<br>{esc(name)}</span>'
                f'<span class="mods" style="justify-content:flex-start">'
                f'<span style="font-size:12.5px;color:var(--fg-faint)">源站未收录</span>'
                f'</span></div>'
            )

    body = f"""
{crumb([("首页", "index.html"), (p["label"], None)], 1)}
<h1 class="page">{esc(p["label"])}</h1>
<p class="sub">共 {len(mods)} 个题型模块。点进任意模块即可精读。</p>
<div class="card">
  <h2><span class="tag">模块</span>选择要练的题型</h2>
  {"".join(cards)}
</div>
"""
    return page(f'{p["label"]} · 六级真题', body, 1)


def module_desc(m, d):
    try:
        if m == "listening":
            return f"{len(d.get('questions', []))} 题 · {len(d.get('transcripts', []))} 篇录音原文"
        if m in ("reading1", "reading2"):
            return f"{len(d.get('questions', []))} 题 · {len(d.get('passages', []))} 段"
        if m == "longreading":
            return f"{len(d.get('statements', []))} 句 · {len(d.get('passages', []))} 段"
        if m == "cloze":
            n = len([r for r in d.get("rows", []) if r.get("tag") == "答案"])
            return f"{n} 空 · 含竞争词辨析"
        if m == "translation":
            return f"{len(d.get('sentences', []))} 句逐句 · 含参考译文"
        if m == "writing":
            return "题目 + 参考范文"
    except Exception:
        pass
    return ""


def float_nav(present, m):
    """右下角浮动条：回到顶部 / 上一篇 / 下一篇（同一套里按题型顺序走）。"""
    i = present.index(m)
    prev_m = present[i - 1] if i else None
    next_m = present[i + 1] if i < len(present) - 1 else None

    def link(mod, arrow, label):
        if not mod:
            return f'<span class="fn off" aria-hidden="true">{arrow}</span>'
        return (f'<a class="fn" href="{mod}.html" title="{label}：{esc(MODULE_NAMES[mod])}" '
                f'aria-label="{label} {esc(MODULE_NAMES[mod])}">{arrow}</a>')

    return ('<div class="floatnav">'
            '<a class="fn" href="#top" title="回到顶部" aria-label="回到顶部">↑</a>'
            + link(prev_m, '←', '上一篇')
            + link(next_m, '→', '下一篇')
            + '</div>')


def hfw_card(m, s):
    """模块页底部的「本篇重点词」折叠块（默认收起的 details）。

    内容由 word.js 拉到 hfw/<set>.json 后按 mods 字段过滤填充。
    写作/翻译没有词表，源站未收录词表的套次也不出这块 —— 免得留空白卡片和 404 请求。
    """
    if m not in HFW_MODULES:
        return ""
    if not os.path.exists(os.path.join(DATA, "hfw", s + ".json")):
        return ""
    return (
        f'<details class="card hfw-card" id="hfwBox" data-mod="{esc(m)}" hidden>'
        '<summary><span class="tag">重点词</span>'
        '<span class="hfw-sum" id="hfwSum">本篇重点词</span>'
        '<span class="hfw-caret" aria-hidden="true">▾</span></summary>'
        '<div class="hfw-body">'
        '<p class="hfw-note">词后的 A1 / A2 / B1 / B2 / C1 是 <b>CEFR 等级</b>：'
        'A1 最基础、C2 最难，六级主攻 B1、B2。这些词既在本篇出现、又是历年真题高频词。'
        '点任意词可查释义并收进生词本。</p>'
        '<div class="hfw-list" id="hfwList"></div>'
        '</div></details>'
    )


# ================================================================ 模块页

def build_module(p, m):
    s = p["set"]
    d = p["modules"][m]
    name = MODULE_NAMES[m]
    part = MODULE_PARTS[m]

    if m == "listening":
        inner = render_listening(d)
        with_ans = True
    elif m in ("reading1", "reading2"):
        inner = render_reading(d)
        with_ans = True
    elif m == "longreading":
        inner = render_longreading(d)
        with_ans = True
    elif m == "cloze":
        inner = render_cloze(d)
        with_ans = True
    elif m == "translation":
        inner = render_translation(d)
        with_ans = False
    elif m == "writing":
        inner = render_writing(d)
        with_ans = False
    else:
        inner = "<p>暂不支持</p>"
        with_ans = False

    mods = p["modules"]
    nav = ['<div class="modnav">']
    for mm in MODULE_ORDER:
        cls = "" if mm in mods else " off"
        href = f"{mm}.html" if mm in mods else "#"
        cur = ' style="border-color:var(--accent)"' if mm == m else ""
        nav.append(f'<a class="{cls.strip()}" href="{href}"{cur}>{icon(mm)}'
                   f'<span class="mt">{MODULE_NAMES[mm]}</span>'
                   f'<span class="n">{MODULE_PARTS[mm]}</span></a>')
    nav.append("</div>")

    body = f"""
{crumb([("首页", "index.html"), (p["label"], f"p/{s}.html"), (name, None)], 2)}
<h1 class="page">{esc(part)} · {esc(name)}</h1>
<p class="sub">{esc(p["label"])}</p>
{"".join(nav)}
{tools_bar(with_ans)}
{ANSHINT if with_ans else ""}
{inner}
{hfw_card(m, s)}
{float_nav([mm for mm in MODULE_ORDER if mm in mods], m)}
"""
    return page(f'{p["label"]} {name} · 六级真题解析', body, 2,
                body_class="hide-ans" if with_ans else "")


# ---------------------------------------------------------------- 听力

def render_listening(d):
    out = []
    # 录音原文
    trs = d.get("transcripts", [])
    if trs:
        out.append('<div class="card"><h2><span class="tag">原文</span>听力录音文字稿</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '考卷上只有选项，题目由录音念出。这里是完整原文与逐句中译——听不懂时对照它。'
                   '先听、再对原文、然后模仿跟读。</p>')
        for t in trs:
            out.append('<div class="piece">')
            out.append('<div class="piece-head"><span>' + esc(t.get("head", "")) + '</span>')
            if t.get("seek"):
                out.append(f'<span class="seek">{esc(t["seek"])}s</span>')
            out.append('</div>')
            for ln in t.get("lines", []):
                out.append('<div class="tr-line">')
                out.append(f'<span class="no">{ln.get("idx", "")}</span>')
                if ln.get("en"):
                    out.append(f'<p class="en">{esc(ln["en"])}</p>')
                if ln.get("zh"):
                    out.append(f'<p class="zh">{esc(ln["zh"])}</p>')
                out.append('</div>')
            out.append('</div>')
        out.append('</div>')

    # 题目与解析
    qs = d.get("questions", [])
    if qs:
        out.append('<div class="card"><h2><span class="tag">解析</span>25 题逐题详解</h2>')
        secs = {x["section"]: x for x in d.get("sections", [])}
        cur_sec = None
        sec_names = {"A": "Section A · 长对话", "B": "Section B · 听力篇章",
                     "C": "Section C · 讲座/讲话"}
        for q in qs:
            no = q["no"]
            for sname, sdata in secs.items():
                if sdata["from"] <= no <= sdata["to"] and cur_sec != sname:
                    cur_sec = sname
                    out.append(f'<div class="sec-head">{esc(sec_names.get(sname, sname))}'
                               f'（{sdata["from"]}–{sdata["to"]} 题）</div>')
            out.append(render_question(q, show_passage=False))
        out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------- 阅读

def render_reading(d):
    out = []
    pas = d.get("passages", [])
    if pas:
        out.append('<div class="card"><h2><span class="tag">原文</span>逐段精读</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '每段英文下是中译。遇到生词查出来写旁边，再回头读生词所在的句子。')
        out.append('</p>')
        for p_ in pas:
            out.append('<div class="para">')
            out.append(f'<span class="pno">P{p_["no"]}</span>')
            if p_.get("en"):
                out.append(f'<p class="en">{esc(p_["en"])}</p>')
            if p_.get("zh"):
                out.append(f'<p class="zh">{esc(p_["zh"])}</p>')
            out.append('</div>')
        out.append('</div>')

    qs = d.get("questions", [])
    if qs:
        out.append('<div class="card"><h2><span class="tag">解析</span>逐题详解</h2>')
        for q in qs:
            out.append(render_question(q))
        out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------- 长篇阅读

def render_longreading(d):
    out = []
    pas = d.get("passages", [])
    if pas:
        out.append('<div class="card"><h2><span class="tag">原文</span>分段标注</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '信息匹配题：先读下面的陈述句，再回到这里找它出自哪一段。'
                   '每段标了字母（A、B、C…），就是答案要填的；下拉框里也带了每段首句作提示。')
        out.append('</p>')
        for p_ in pas:
            out.append('<div class="para">')
            out.append(f'<span class="pno">{para_letter(p_["no"])}</span>')
            if p_.get("en"):
                out.append(f'<p class="en">{esc(p_["en"])}</p>')
            if p_.get("zh"):
                out.append(f'<p class="zh">{esc(p_["zh"])}</p>')
            out.append('</div>')
        out.append('</div>')

    sts = d.get("statements", [])
    if sts:
        out.append('<div class="card"><h2><span class="tag">解析</span>逐句定位</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '每题右侧下拉选它出自哪一段（A、B、C…）。选完点底部「提交答案」判分。</p>')
        for st in sts:
            a0 = st.get("analysis", {})
            p0 = a0.get("para", "")
            if not p0:
                pm0 = re.search(r'([A-Z])\s*段', a0.get("答案", ""))
                p0 = pm0.group(1) if pm0 else ""
            out.append(f'<div class="q" data-qno="{esc(str(st["no"]))}" '
                       f'data-answer="{esc(p0)}" data-qtype="match">')
            out.append('<div class="q-head">')
            out.append(f'<span class="q-no">{st["no"]}</span>')
            out.append('<div class="q-stem">')
            if st.get("en"):
                out.append(f'<p class="en" style="margin:0">{esc(st["en"])}</p>')
            if st.get("zh"):
                out.append(f'<p class="zh">{esc(st["zh"])}</p>')
            out.append('</div></div>')
            a = st.get("analysis", {})
            para = a.get("para", "")
            if not para:
                pm = re.search(r'([A-Z])\s*段', a.get("答案", ""))
                para = pm.group(1) if pm else ""
            if para:
                out.append(f'<div class="ansbadge" hidden>答案：{esc(para)} 段</div>')
            rows = [(k, v) for k, v in a.items() if k not in ("答案", "para")]
            if rows:
                out.append('<div class="ana">')
                for k, v in rows:
                    out.append(f'<div class="row"><span class="tag">{esc(k)}</span>'
                               f'<span class="txt">{esc(v)}</span></div>')
                out.append('</div>')
            out.append('</div>')
        out.append('</div>')
    return "".join(out)


def para_letter(n):
    """1->A, 2->B ... 26->Z, 27->AA"""
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ---------------------------------------------------------------- 选词填空

def render_cloze(d):
    out = []
    rows = d.get("rows", [])
    passages = d.get("passages", [])
    bank = d.get("wordbank", [])
    if not rows and not passages:
        return '<p>无数据</p>'

    # ---- 1) 带空短文（空位 = 可点击槽） ----
    if passages:
        out.append('<div class="card"><h2><span class="tag">原文</span>带空短文</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '先读全文把握大意，再回到空格处：点一个空，再从下面词库点一个词填进去。'
                   '填完点底部「提交答案」判分。</p>')
        out.append('<div class="cloze-text">')
        for p_ in passages:
            out.append('<div class="para">')
            out.append(f'<span class="pno">P{p_["no"]}</span>')
            if p_.get("en"):
                out.append('<p class="en">' + cloze_slots(p_["en"]) + '</p>')
            if p_.get("zh"):
                out.append(f'<p class="zh">{esc(p_["zh"])}</p>')
            out.append('</div>')
        out.append('</div></div>')

    # ---- 2) 词库（可点击选词） ----
    if bank:
        out.append('<div class="card"><h2><span class="tag">词库</span>'
                   f'{len(bank)} 词选 10</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '点一个词选中它，再点文中空格填入；点已填入的空可退回词库。每词最多用一次。'
                   '（跟真题一样，这里只给裸单词 —— 词性和释义默认藏起来，'
                   '点上方「显示答案」才出现。）</p>')
        out.append('<ul class="wordbank">')
        for w in bank:
            out.append(
                f'<li class="wb-item" data-letter="{esc(w["letter"])}" '
                f'data-word="{esc(w["word"])}" tabindex="0" role="button">'
                f'<span class="wb-l">{esc(w["letter"])}</span>'
                f'<span class="wb-w">{esc(w["word"])}</span>'
                f'<span class="wb-p">{esc(w["pos"])}</span>'
                f'<span class="wb-g">{esc(w["gloss"])}</span>'
                f'</li>')
        out.append('</ul></div>')

    # 按【答案】分组成一空一块
    groups = []
    cur = None
    for r in rows:
        if r.get("tag") == "答案":
            cur = {"answer": r.get("text", ""), "items": []}
            groups.append(cur)
        elif cur is not None:
            cur["items"].append((r.get("tag", ""), r.get("text", "")))

    out.append('<div class="card"><h2><span class="tag">解析</span>逐空详解</h2>')
    out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
               '选词填空 10 空。每空给出词性依据、上下文依据、同词性竞争词辨析、易错提示。</p>')
    for gi, g in enumerate(groups, 1):
        am = re.search(r'([A-O])', g["answer"])
        letter = am.group(1) if am else ""
        # 空号不在答案文本里（形如 "N) surpass动词"），按出现顺序推：26 起
        nm = re.search(r'\d+', g["answer"])
        no = nm.group(0) if nm else str(25 + gi)
        out.append(f'<div class="q" data-qno="{esc(no)}" data-answer="{esc(letter)}" '
                   f'data-qtype="cloze">')
        out.append('<div class="q-head"><span class="q-no">'
                   f'第 {esc(no)} 空</span></div>')
        out.append(f'<div class="ansbadge" hidden>{esc(g["answer"])}</div>')
        out.append('<div class="ana">')
        for tag, txt in g["items"]:
            out.append(f'<div class="row"><span class="tag">{esc(tag)}</span>'
                       f'<span class="txt">{esc(txt)}</span></div>')
        out.append('</div></div>')
    out.append('</div>')
    return "".join(out)


def cloze_slots(en):
    """把 __(26)__ 占位符渲染成可点击的空位槽。"""
    def repl(m):
        no = m.group(1)
        return (f'<span class="cslot" data-qno="{no}" tabindex="0" role="button" '
                f'aria-label="第 {no} 空"><i class="cno">{no}</i>'
                f'<b class="cval"></b></span>')
    return re.sub(r'__\((\d+)\)__', repl, esc(en))


# ---------------------------------------------------------------- 翻译

def render_translation(d):
    out = []
    src = d.get("source_zh", "")
    ref = d.get("reference_en", "")

    out.append('<div class="card"><h2><span class="tag">题目</span>中文原文</h2>')
    out.append(f'<div class="zhblock">{esc(src)}</div>')
    out.append('</div>')

    if ref:
        out.append('<div class="card"><h2><span class="tag">参考</span>整篇参考译文</h2>')
        out.append(f'<div class="enblock">{esc(ref)}</div>')
        out.append('</div>')

    # 主旨 / 时态
    mi, te = d.get("main_idea"), d.get("tense")
    if mi or te:
        out.append('<div class="card"><h2><span class="tag">通读</span>主旨与时态</h2>')
        out.append('<div class="ana">')
        if mi:
            out.append(f'<div class="row"><span class="tag">主旨</span>'
                       f'<span class="txt"><strong>{esc(mi.get("core",""))}</strong><br>'
                       f'{esc(mi.get("detail",""))}</span></div>')
        if te:
            out.append(f'<div class="row"><span class="tag">时态</span>'
                       f'<span class="txt"><strong>{esc(te.get("core",""))}</strong><br>'
                       f'{esc(te.get("detail",""))}</span></div>')
        out.append('</div></div>')

    # 译法（专名/文化词）
    tn = d.get("term_notes", [])
    if tn:
        out.append('<div class="card"><h2><span class="tag">译法</span>专名与文化词</h2>')
        out.append('<div class="ana">')
        for t in tn:
            out.append(f'<div class="row"><span class="tag">{esc(t.get("core",""))}</span>'
                       f'<span class="txt">{esc(t.get("detail",""))}</span></div>')
        out.append('</div></div>')

    # 衔接
    co = d.get("cohesion", [])
    if co:
        out.append('<div class="card"><h2><span class="tag">衔接</span>句间怎么连</h2>')
        out.append('<div class="ana">')
        for c in co:
            out.append(f'<div class="row"><span class="tag">衔接</span>'
                       f'<span class="txt"><strong>{esc(c.get("core",""))}</strong><br>'
                       f'{esc(c.get("detail",""))}</span></div>')
        out.append('</div></div>')

    # 逐句
    ss = d.get("sentences", [])
    if ss:
        out.append('<div class="card"><h2><span class="tag">逐句</span>一句一句翻</h2>')
        out.append('<p style="font-size:13px;color:var(--fg-faint);margin:-4px 0 14px">'
                   '先自己翻一遍，再看「主干／降级／语法」，最后看定稿英译。</p>')
        for s in ss:
            out.append('<div class="sent">')
            out.append(f'<div class="sn">第 {s["no"]} 句</div>')
            if s.get("zh"):
                out.append(f'<p class="zh" style="margin-bottom:8px">{esc(s["zh"])}</p>')
            if s.get("en"):
                out.append(f'<p class="en" style="margin-bottom:8px">{esc(s["en"])}</p>')
            steps = s.get("steps", [])
            if steps:
                out.append('<div class="ana">')
                for st in steps:
                    out.append(f'<div class="row"><span class="tag">{esc(st.get("tag",""))}</span>'
                               f'<span class="txt">{esc(st.get("text",""))}</span></div>')
                out.append('</div>')
            out.append('</div>')
        out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------- 写作

def render_writing(d):
    out = []
    dr = d.get("directions", "")
    if dr:
        out.append('<div class="card"><h2><span class="tag">题目</span>写作要求</h2>')
        out.append(f'<p style="font-size:14.5px;color:var(--fg-soft);white-space:pre-wrap">{esc(dr)}</p>')
        out.append('</div>')
    sm = d.get("sample_en", "")
    if sm:
        out.append('<div class="card"><h2><span class="tag">范文</span>参考范文</h2>')
        for para in [x for x in sm.split("\n") if x.strip()]:
            out.append(f'<p class="en" style="margin-bottom:12px">{esc(para)}</p>')
        out.append('</div>')
    for b in d.get("blocks", []):
        out.append('<div class="card"><h2><span class="tag">拆解</span>' + esc(b.get("kind", "")) + '</h2>')
        out.append(f'<div class="ana"><div class="row"><span class="txt">{esc(b.get("text",""))}</span></div></div>')
        out.append('</div>')
    return "".join(out)


# ---------------------------------------------------------------- 题目组件

def render_question(q, show_passage=True):
    out = ['<div class="q" data-qno="%s" data-answer="%s" data-qtype="choice">' % (esc(str(q.get('no', ''))), esc(q.get('answer', '')))]
    out.append('<div class="q-head">')
    out.append(f'<span class="q-no">{q["no"]}</span>')
    out.append('<div class="q-stem">')
    if q.get("stem"):
        out.append(f'<p class="en" style="margin:0">{esc(q["stem"])}</p>')
    if q.get("stem_zh"):
        out.append(f'<p class="zh">{esc(q["stem_zh"])}</p>')
    out.append('</div></div>')

    # 选项（正确项着色）
    oa = {o["letter"]: o for o in q.get("option_analysis", [])}
    ans = q.get("answer", "")
    if q.get("options"):
        out.append('<ul class="opts" data-quiz="pick">')
        for o in q["options"]:
            ltr = o["letter"]
            out.append(f'<li class="quiz-option" data-value="{esc(ltr)}" data-letter="{esc(ltr)}">')
            out.append(f'<span class="ltr">{esc(ltr)})</span>')
            out.append('<span class="otxt">')
            if o.get("text"):
                out.append(f'<span class="en" style="display:block;margin:0">{esc(o["text"])}</span>')
            if o.get("zh"):
                out.append(f'<span class="zh" style="display:block">{esc(o["zh"])}</span>')
            out.append('</span></li>')
        out.append('</ul>')

    # 答案 + 解析：整块套一个可折叠的 details（默认展开，想扫读时可以逐个收起）
    out.append('<details class="qana" open><summary>解析</summary>')

    if ans:
        out.append(f'<div class="ansbadge">{esc(ans)}'
                   f'<span class="qt">{esc(q.get("qtype", ""))}</span></div>')

    # 选项逐个分析
    if oa:
        for ltr in sorted(oa):
            o = oa[ltr]
            flag = o.get("flag", "")
            fc = "ok" if o.get("correct") else ("bad" if flag else "neutral")
            out.append('<div class="oa">')
            out.append(f'<span class="flag {fc}">{esc(ltr)}) {esc(flag)}</span>')
            if o.get("note"):
                out.append(esc(o["note"]))
            if o.get("reason"):
                out.append(' ' + esc(o["reason"]))
            if o.get("pairs"):
                out.append('<ul class="pairs">')
                for pr in o["pairs"]:
                    out.append(f'<li><span class="orig">{esc(pr["orig"])}</span>'
                               f'<span class="arrow">↔</span>'
                               f'<span class="opt">{esc(pr["opt"])}</span></li>')
                out.append('</ul>')
            out.append('</div>')

    # 定位
    loc = q.get("locate") or {}
    if loc.get("en") or loc.get("zh"):
        out.append('<div class="locate">')
        if loc.get("para"):
            out.append(f'<span class="pn">{esc(loc["para"])}</span> ')
        if loc.get("en"):
            out.append(f'<p class="en" style="margin:4px 0 2px;font-size:15px">{esc(loc["en"])}</p>')
        if loc.get("zh"):
            out.append(f'<p class="zh" style="margin:0">{esc(loc["zh"])}</p>')
        out.append('</div>')

    # 其他解析行（判型/拆句/信号/替换/排除…）
    ana = q.get("analysis", {})
    if ana:
        out.append('<div class="ana">')
        order = ["判型", "拆句", "信号", "替换", "排除", "锚点", "改写", "辨邻", "易错", "竞争词"]
        keys = [k for k in order if k in ana] + [k for k in ana if k not in order]
        for k in keys:
            out.append(f'<div class="row"><span class="tag">{esc(k)}</span>'
                       f'<span class="txt">{esc(ana[k])}</span></div>')
        out.append('</div>')

    out.append('</details>')
    out.append('</div>')
    return "".join(out)


# ================================================================ 专项页

def build_section(m, meta, papers):
    """某题型跨全部套次的横向列表。"""
    rows = []
    for p in meta["papers"]:
        if m not in p["modules"]:
            continue
        rows.append(
            f'<a class="setrow" href="../p/{p["set"]}/{m}.html">'
            f'<span class="lbl">{esc(p["label"])}</span>'
            f'<span class="mods" style="justify-content:flex-end">'
            f'<span style="font-size:12px;color:var(--fg-faint)">'
            f'{esc(module_desc(m, papers[p["set"]]["modules"][m]))}</span>'
            f'</span></a>'
        )
    body = f"""
{crumb([("首页", "index.html"), (MODULE_NAMES[m], None)], 1)}
<h1 class="page">{esc(MODULE_NAMES[m])} · 专项训练</h1>
<p class="sub">{esc(MODULE_PARTS[m])} · 共 {len(rows)} 套 · 同一题型横向刷，找规律</p>
<div class="card">
  <h2><span class="tag">列表</span>按考期倒序</h2>
  {"".join(rows) if rows else "<p>暂无</p>"}
</div>
"""
    return page(f'{MODULE_NAMES[m]} 专项 · 六级真题', body, 1)


# ================================================================ 重点词页

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
LEVEL_DESC = {
    "A1": "入门", "A2": "基础", "B1": "中级·六级起点",
    "B2": "六级主力", "C1": "高级·拉分", "C2": "精通",
}


def build_hfw(meta):
    """全局重点词页：等级分布在这里算好写进 HTML，词表由 word.js 渲染 dict.json。"""
    with open(os.path.join(DATA, "dict.json"), encoding="utf-8") as f:
        words = json.load(f)["words"]
    cnt = {}
    for w in words.values():
        lv = w.get("cefr", "")
        cnt[lv] = cnt.get(lv, 0) + 1
    total = sum(cnt.values())

    chips = [f'<button class="lvchip on" data-lv="">全部<i class="lv-n">{total}</i></button>']
    for lv in LEVELS:
        if not cnt.get(lv):
            continue
        chips.append(f'<button class="lvchip" data-lv="{lv}">{lv}'
                     f'<i class="lv-n">{cnt[lv]}</i><em>{esc(LEVEL_DESC[lv])}</em></button>')

    body = f"""
{crumb([("首页", "index.html"), ("重点词", None)], 0)}
<div class="hero hero-art hero-splash">
  <h1>真题重点词</h1>
  <p>各套解析页附的「真题高频词」汇总去重后共 <b>{total}</b> 词，默认按累计出现次数排序。</p>
</div>
<div class="card">
  <h2><span class="tag">等级</span>CEFR 等级怎么看</h2>
  <p class="hfw-note"><b>A1 / A2</b> 入门基础（多半已经会）· <b>B1 / B2</b> 中级，
  六级阅读的生词主要在这一档，优先背 · <b>C1 / C2</b> 高级，认识即可，考到就是拉分项。
  点一下只看该等级。</p>
  <div class="lvrow" id="hfwLevels">{"".join(chips)}</div>
</div>
<div class="card">
  <div class="hfwtools">
    <input id="hfwSearch" type="search" placeholder="搜索单词或中文释义…" autocomplete="off">
    <span class="hfw-total" id="hfwTotal"></span>
  </div>
  <div class="hfw-list hfw-page" id="hfwPage"></div>
  <button class="mebtn hfw-more" id="hfwMore" hidden></button>
</div>
"""
    return page("真题重点词 · 六级真题精读", body, 0,
                "六级历年真题高频词总表，按 CEFR 等级与出现频次整理")


# ================================================================ 我的学习页

def build_me(meta):
    """生词本 / 错题本 / 句子收藏。数据在 localStorage，这里只出骨架，word.js 渲染。"""
    labels = {
        "sets": {p["set"]: p["label"] for p in meta["papers"]},
        "mods": MODULE_NAMES,
    }
    extra_js = ('<script>window.CET6_LABELS = '
                + json.dumps(labels, ensure_ascii=False, separators=(",", ":"))
                + ';</script>')
    body = f"""
{crumb([("首页", "index.html"), ("我的学习", None)], 0)}
<h1 class="page">我的学习</h1>
<p class="sub">生词本 · 错题本 · 句子收藏。数据只存在这台设备的浏览器里 —— 换设备或清缓存会丢，
可以点「导出 JSON」备份。</p>
<div class="card">
  <div class="tabs">
    <button class="tab on" data-tab="vocab">生词本 <span class="vcount" id="cntVocab">0</span></button>
    <button class="tab" data-tab="wrong">错题本 <span class="vcount" id="cntWrong">0</span></button>
    <button class="tab" data-tab="sents">句子 <span class="vcount" id="cntSents">0</span></button>
  </div>
  <div class="me-bar">
    <input id="meSearch" type="search" placeholder="搜索…" autocomplete="off">
    <button class="mebtn" id="meExport">导出 JSON</button>
    <button class="mebtn" id="meClear">清空当前</button>
  </div>
</div>
<div class="card" id="meRoot">
  <div id="meList"></div>
</div>
"""
    return page("我的学习 · 六级真题精读", body, 0,
                "生词本、错题本、句子收藏，只存在本机浏览器", extra_js=extra_js)


# ================================================================ app.js

APP_JS = r"""// 六级真题精读站 · 交互

// 主题三档循环：浅色 → 深色 → 纯黑（OLED，夜里看更省电更不刺眼）
var THEMES = ['light', 'dark', 'oled'];

function curTheme() {
  var t = document.documentElement.dataset.theme;
  return THEMES.indexOf(t) >= 0 ? t : 'light';
}

function toggleTheme() {
  var next = THEMES[(THEMES.indexOf(curTheme()) + 1) % THEMES.length];
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('cet6-theme', next); } catch (e) {}
  syncButtons();
}

function toggleZh() {
  document.body.classList.toggle('no-zh');
  try {
    localStorage.setItem('cet6-nozh', document.body.classList.contains('no-zh') ? '1' : '0');
  } catch (e) {}
  syncButtons();
}

function toggleAns() {
  document.body.classList.toggle('hide-ans');
  try {
    localStorage.setItem('cet6-noans', document.body.classList.contains('hide-ans') ? '1' : '0');
  } catch (e) {}
  syncButtons();
}

function syncButtons() {
  var t = curTheme();
  var nozh = document.body.classList.contains('no-zh');
  var noans = document.body.classList.contains('hide-ans');
  setText('themeBtn', t === 'light' ? '◐' : (t === 'dark' ? '◑' : '☀'));
  setText('themeBtn2', t === 'light' ? '深色' : (t === 'dark' ? '纯黑' : '浅色'));
  setText('zhBtn', nozh ? '显示中文' : '中文对照');
  setText('ansBtn', noans ? '显示答案' : '隐藏答案');
  var b = document.getElementById('zhBtn'); if (b) b.classList.toggle('on', !nozh);
}

function setText(id, t) {
  var e = document.getElementById(id);
  if (e) e.textContent = t;
}

// 初始化：恢复用户偏好
(function () {
  try {
    var th = localStorage.getItem('cet6-theme');
    if (th) document.documentElement.dataset.theme = th;
    else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      document.documentElement.dataset.theme = 'dark';
    if (localStorage.getItem('cet6-nozh') === '1') document.body.classList.add('no-zh');
    // 答案默认隐藏：只在有答案的页面（body 初始就带 hide-ans）
    if (localStorage.getItem('cet6-noans') === '0') document.body.classList.remove('hide-ans');
  } catch (e) {}
})();

// 键盘快捷键
 document.addEventListener('keydown', function (e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === 'a' || e.key === 'A') toggleAns();
  if (e.key === 'z' || e.key === 'Z') toggleZh();
  if (e.key === 'd' || e.key === 'D') toggleTheme();
});

window.addEventListener('DOMContentLoaded', syncButtons);
"""


# ================================================================ 主流程

TOTAL_SETS = 0
TOTAL_MODULES = 0


def main():
    global TOTAL_SETS, TOTAL_MODULES

    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        meta = json.load(f)
    TOTAL_SETS = meta["total_sets"]
    TOTAL_MODULES = meta["total_modules"]

    papers = {}
    pdir = os.path.join(DATA, "paper")
    for fn in os.listdir(pdir):
        if fn.endswith(".json"):
            with open(os.path.join(pdir, fn), encoding="utf-8") as f:
                d = json.load(f)
            papers[d["set"]] = d

    # 目录
    for sub in ("p", "section", "assets"):
        os.makedirs(os.path.join(SITE, sub), exist_ok=True)

    # 资源（style.css / word.js 已直接放在 site/assets/ 下，这里只生成 app.js）
    with open(os.path.join(SITE, "assets", "app.js"), "w", encoding="utf-8") as f:
        f.write(APP_JS)

    # 词库：dict.json 与每套的 hfw/<set>.json 拷到站点根
    import shutil as _sh
    dd = os.path.join(DATA, "dict.json")
    if os.path.exists(dd):
        _sh.copy(dd, os.path.join(SITE, "dict.json"))
        print("  dict.json")
    da = os.path.join(DATA, "dict_all.json")
    if os.path.exists(da):
        _sh.copy(da, os.path.join(SITE, "dict_all.json"))
        print("  dict_all.json（兜底词库，%d KB）" % (os.path.getsize(da) // 1024))
    hs = os.path.join(DATA, "hfw")
    if os.path.isdir(hs):
        dst = os.path.join(SITE, "hfw")
        os.makedirs(dst, exist_ok=True)
        n = 0
        for fn in os.listdir(hs):
            if fn.endswith(".json"):
                _sh.copy(os.path.join(hs, fn), os.path.join(dst, fn))
                n += 1
        print(f"  hfw/ ({n} 个词表)")

    # 首页
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(meta))
    print("  index.html")

    # 套卷页 + 模块页
    n_paper = n_mod = 0
    for p in meta["papers"]:
        s = p["set"]
        full = papers.get(s)
        if not full:
            continue
        with open(os.path.join(SITE, "p", s + ".html"), "w", encoding="utf-8") as f:
            f.write(build_paper(full, meta))
        n_paper += 1

        mdir = os.path.join(SITE, "p", s)
        os.makedirs(mdir, exist_ok=True)
        for m in full["modules"]:
            with open(os.path.join(mdir, m + ".html"), "w", encoding="utf-8") as f:
                f.write(build_module(full, m))
            n_mod += 1
    print(f"  {n_paper} 个套卷页, {n_mod} 个模块页")

    # 专项页
    n_sec = 0
    for m in MODULE_ORDER:
        if not any(m in p["modules"] for p in meta["papers"]):
            continue
        with open(os.path.join(SITE, "section", m + ".html"), "w", encoding="utf-8") as f:
            f.write(build_section(m, meta, papers))
        n_sec += 1
    print(f"  {n_sec} 个专项页")

    # 两个独立页面（顶栏链接一直指着它们，别再只写链接不生成页面）
    with open(os.path.join(SITE, "hfw.html"), "w", encoding="utf-8") as f:
        f.write(build_hfw(meta))
    print("  hfw.html")
    with open(os.path.join(SITE, "me.html"), "w", encoding="utf-8") as f:
        f.write(build_me(meta))
    print("  me.html")

    print(f"\n站点输出: {SITE}")


if __name__ == "__main__":
    main()
