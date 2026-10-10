# -*- coding: utf-8 -*-
"""
解析「阅读理解（四选一）」解析页 -> JSON。

页面结构（实测，带语义锚点，优先用锚点而非文本猜测）：

文章段落：
  <div id="p-1">
    <span class="exam-pno">P1</span>English...
    <p class="lt-zh">中译</p>
  </div>

题目（id 是 qp-NN 而不是 q-NN）：
  <div id="qp-46" class="exam-q lqp-paper">
    <div>46.</div>
    <span data-pdh-stem>题干英文</span>
    <span data-pdh-letter="A">选项A英文</span> ... B/C/D
  </div>
  <p class="lqp-stem">题干中译</p>
  <ul class="lqp-trans-choices">
    <li><span class="lqp-trans-letter">A)</span> 选项A中译</li> ...
  </ul>

解析（跟在同一容器里）：
  <div class="rp-ana" aria-label="第 46 题解析">
    <div class="rp-row rp-row--answer">
      <span class="rp-tag">【答案】</span>
      <div class="rp-answer-line"><strong class="rp-ans">B</strong>
           <span class="rp-qtype">（细节题）</span></div>
    <div class="rp-row"><span class="rp-tag">【判型】</span><p class="rp-text">...</p></div>
    <div class="rp-row"><span class="rp-tag">【拆句】</span><p class="rp-text">...</p></div>
    <div class="rp-row"><span class="rp-tag">【定位】</span>
      <div class="rp-locate">
        <a class="rp-locate-p">P1</a>
        <p class="rp-locate-en">定位英文</p>
        <p class="rp-locate-zh">定位中译</p>
    <div class="rp-row"><span class="rp-tag">【选项】</span>
      <ul class="rp-verdicts">
        <li class="is-bad rp-verdict">
          <div class="rp-verdict-head"><span class="rp-verdict-letter">A)</span>
               <span class="rp-flag rp-flag--bad">与原文相反</span></div>
          <p class="rp-verdict-note">解释</p>
        <li class="is-ok rp-verdict">
          ... <ul class="rp-pairs">
            <li class="rp-pair">
              <span class="rp-pair-orig">原文</span>
              <span class="rp-pair-arrow">↔</span>
              <span class="rp-pair-opt">选项</span>

也可能有 【句子精讲】/【高频词】 等后续块，本解析器只取上表这些。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_lib import (  # noqa: E402
    strip_scripts, to_text, one_line, elem_span, h1_text,
)


# ------------------------------------------------------------ 段落

def parse_passages(h):
    """抽文章段落：id=p-N，每段含英文 + 中译。"""
    paras = []
    seen = set()
    for m in re.finditer(r'id="p-(\d+)"', h):
        no = int(m.group(1))
        if no in seen:
            continue
        lt = h.rfind("<", 0, m.start())
        sp = elem_span(h, lt)
        if not sp:
            continue
        inner = h[sp[0]:sp[1]]
        zh = ""
        zm = re.search(r'(?s)<p[^>]*class="[^"]*lt-zh[^"]*"[^>]*>(.*?)</p>', inner)
        if zm:
            zh = one_line(zm.group(1))
            en_part = inner[:zm.start()] + inner[zm.end():]
        else:
            en_part = inner
        en_part = re.sub(r'(?s)<span[^>]*class="[^"]*exam-pno[^"]*"[^>]*>.*?</span>', '', en_part)
        en = one_line(en_part)
        if en or zh:
            seen.add(no)
            paras.append({"no": no, "en": en, "zh": zh})
    paras.sort(key=lambda x: x["no"])
    return paras


# ------------------------------------------------------------ 题目

def parse_questions(h):
    """抽题干与选项：用 data-pdh-stem / data-pdh-letter / lqp-stem / lqp-trans-choices。"""
    qs = []
    for m in re.finditer(r'id="qp-(\d+)"', h):
        no = int(m.group(1))
        lt = h.rfind("<", 0, m.start())
        sp = elem_span(h, lt)
        if not sp:
            continue
        inner = h[sp[0]:sp[1]]

        # 题干（英文）
        sm = re.search(r'(?s)data-pdh-stem[^>]*>(.*?)</span>', inner)
        stem = one_line(sm.group(1)) if sm else ""

        # 选项（英文）
        opts = []
        for om in re.finditer(r'(?s)data-pdh-letter="([A-D])"[^>]*>(.*?)</span>', inner):
            opts.append({"letter": om.group(1), "text": one_line(om.group(2)), "zh": ""})

        # 题干中译与选项中译在题干容器【外面】（兄弟节点），
        # 所以从 qp-NN 元素结束处往后取一段作为「题目区」
        tail = h[sp[2]: sp[2] + 6000] if sp[2] < len(h) else ""

        # 题干中译：<p class="lqp-stem">
        zsm = re.search(r'(?s)<p[^>]*class="[^"]*lqp-stem[^"]*"[^>]*>(.*?)</p>', tail)
        stem_zh = one_line(zsm.group(1)) if zsm else ""

        # 选项中译：<ul class="lqp-trans-choices"> 里每 li
        um = re.search(r'(?s)<ul[^>]*class="[^"]*lqp-trans-choices[^"]*"[^>]*>(.*?)</ul>', tail)
        if um:
            zh_map = {}
            for lm in re.finditer(r'(?s)<li[^>]*>(.*?)</li>', um.group(1)):
                seg = lm.group(1)
                lm2 = re.search(r'lqp-trans-letter[^>]*>\s*([A-D])', seg)
                if lm2:
                    body = re.sub(r'(?s)<span[^>]*class="[^"]*lqp-trans-letter[^"]*"[^>]*>.*?</span>', '', seg)
                    zh_map[lm2.group(1)] = one_line(body)
            for o in opts:
                o["zh"] = zh_map.get(o["letter"], "")

        # 解析块：跟在题干容器后面的 <div class="rp-ana" aria-label="第 NN 题解析">
        ana = {}
        am = re.search(r'<div class="rp-ana"[^>]*aria-label="第\s*' + str(no) + r'\s*题解析"[^>]*>', h)
        if am:
            asp = elem_span(h, am.start())
            if asp:
                ana_html = h[am.start():asp[2]]
                ana = parse_analysis(ana_html)

        if stem or opts:
            q = {"no": no, "stem": stem, "stem_zh": stem_zh, "options": opts}
            q.update(ana)
            qs.append(q)

    qs.sort(key=lambda x: x["no"])
    return qs


# ------------------------------------------------------------ 解析

ANA_KINDS = ["答案", "判型", "拆句", "主旨", "结构", "信号", "替换", "排除",
             "译法", "时态", "定位", "选项", "语句", "词汇"]


def parse_analysis(seg):
    """从 rp-ana 片段里抽解析内容。"""
    out = {}

    # 答案
    am = re.search(r'(?s)class="rp-ans"[^>]*>(.*?)</strong>', seg)
    if am:
        out["answer"] = one_line(am.group(1))
    tm = re.search(r'(?s)class="rp-qtype"[^>]*>(.*?)</span>', seg)
    if tm:
        out["qtype"] = one_line(tm.group(1))

    # 各个 【xx】 行
    for m in re.finditer(r'<div class="rp-row[^"]*"[^>]*>(.*?)</div>\s*(?=<div class="rp-row|<div class="rp-ana|</div>\s*</div>|$)', seg, re.S):
        row = m.group(1)
        tm = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
        if not tm:
            continue
        tag = one_line(tm.group(1)).strip("【】 ")
        if tag in ("答案", "选项"):
            continue
        # 取该行的正文（去掉 tag 后的内容）
        body = row[tm.end():]
        txt = one_line(body)
        if tag and txt:
            out[tag] = txt

    # 定位（单独结构化）
    lm = re.search(r'(?s)<div class="rp-locate"[^>]*>(.*?)</div>\s*(?=</div>|<div class="rp-row)', seg)
    if lm:
        loc = lm.group(1)
        # 只在 <a class="...rp-locate-p..."> 的闭合尖括号之后取 Pn
        pm = re.search(r'<a\b[^>]*\brp-locate-p\b[^>]*>\s*(P\d+)\s*</a>', loc)
        en = re.search(r'(?s)<p[^>]*rp-locate-en[^>]*>(.*?)</p>', loc)
        zh = re.search(r'(?s)<p[^>]*rp-locate-zh[^>]*>(.*?)</p>', loc)
        out["locate"] = {
            "para": pm.group(1) if pm else "",
            "en": one_line(en.group(1)) if en else "",
            "zh": one_line(zh.group(1)) if zh else "",
        }

    # 选项逐个分析
    opts = []
    um = re.search(r'(?s)<ul class="rp-verdicts"[^>]*>(.*)', seg)
    if um:
        body = um.group(1)
        for li_m in re.finditer(r'<li[^>]*class="([^"]*\brp-verdict\b[^"]*)"[^>]*>', body):
            sp = elem_span(body, li_m.start())
            if not sp:
                break
            item = body[li_m.start():sp[2]]
            letters = re.search(r'rp-verdict-letter[^>]*>\s*([A-D])', item)
            flag = re.search(r'(?s)rp-flag[^>]*>(.*?)</span>', item)
            note = re.search(r'(?s)<p class="rp-verdict-note"[^>]*>(.*?)</p>', item)
            pairs = []
            for pm in re.finditer(r'(?s)<li class="rp-pair"[^>]*>(.*?)</li>', item):
                pseg = pm.group(1)
                o = re.search(r'(?s)rp-pair-orig[^>]*>(.*?)</span>', pseg)
                t = re.search(r'(?s)rp-pair-opt[^>]*>(.*?)</span>', pseg)
                if o and t:
                    pairs.append({"orig": one_line(o.group(1)), "opt": one_line(t.group(1))})
            cls = li_m.group(1)
            opts.append({
                "letter": letters.group(1) if letters else "",
                "correct": "is-ok" in cls,
                "flag": one_line(flag.group(1)) if flag else "",
                "note": one_line(note.group(1)) if note else "",
                "pairs": pairs,
            })
        opts.sort(key=lambda x: x["letter"])
        out["option_analysis"] = opts
        if "answer" not in out:
            for o in opts:
                if o["correct"] and o["letter"]:
                    out["answer"] = o["letter"]
                    break

    return out


# ------------------------------------------------------------ 入口

def parse_html(raw):
    """从原始 HTML 文本解析（供 build_data 调用）。"""
    h = strip_scripts(raw)
    return {
        "title": h1_text(h),
        "passages": parse_passages(h),
        "questions": parse_questions(h),
    }


def parse_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_html(f.read())


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "raw", "2022-06-1", "part3-section-c-1.html")
    d = parse_file(p)
    print("标题:", d["title"])
    print(f"段落 {len(d['passages'])}  题目 {len(d['questions'])}")
    print("\n--- 段落 ---")
    for x in d["passages"][:2]:
        print(f"  P{x['no']} {x['en'][:95]}")
        print(f"     {x['zh'][:60]}")
    print("\n--- 第 1 题完整结构 ---")
    q = d["questions"][0]
    print(f"  题干: {q['stem']}")
    print(f"  中译: {q['stem_zh']}")
    for o in q["options"]:
        print(f"  {o['letter']}) {o['text']}")
        print(f"      {o['zh']}")
    print(f"\n  答案: {q.get('answer')} {q.get('qtype','')}")
    print(f"  判型: {q.get('判型','')[:100]}")
    print(f"  定位: P{q.get('locate',{}).get('para','')} {q.get('locate',{}).get('en','')[:80]}")
    print("  选项分析:")
    for o in q.get("option_analysis", []):
        mk = "✓" if o["correct"] else " "
        print(f"    {mk} {o['letter']}) {o['flag']}")
        print(f"        {o['note'][:90]}")
        for pr in o["pairs"]:
            print(f"        {pr['orig'][:45]} ↔ {pr['opt'][:45]}")
