# -*- coding: utf-8 -*-
"""
解析其余模块 -> JSON：翻译(part-iv)、写作(part1)、选词填空(part3-section-a)、
长篇阅读(part3-section-b)。

各模块结构（实测）：

【翻译 part-iv】
  <div id="stem"> 中文原文 </div>            （卷面中文）
  <div id="final"> 整篇参考英译 </div>        （可能叫别的 class，见下）
  【衔接】<ul class="tp-list"><li><strong class="tp-core">标题</strong>
      <span class="tp-detail">说明</span></li>
  【主旨】<div class="rp-row"><p class="rp-text"><strong class="tp-core">主旨</strong>
      <span class="tp-detail">...</span>
  【时态】同上
  【译法】<ul class="tp-list"><li class="tqp-chunk"><strong class="tp-core">词</strong>
      <span class="tp-detail">...</span>
  逐句解析 <div id="parsing" class="tqp">
      <div class="tqp-unit"><div class="tqp-stem">中文句</div>
          <div class="tqp-strategy">策略</div><div class="tqp-final">英译</div>

【写作 part1】
  题目 Directions + 范文（结构待实测确认）

【选词填空 part3-section-a】/【长篇阅读 part3-section-b】
  结构待实测确认
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_lib import (  # noqa: E402
    strip_scripts, to_text, one_line, elem_span, h1_text, find_blocks,
)


# ================================================================ 通用小工具

def grab_tp_pair(frag):
    """取 <strong class="tp-core">标题</strong><span class="tp-detail">说明</span>。"""
    c = re.search(r'(?s)tp-core[^>]*>(.*?)</strong>', frag)
    d = re.search(r'(?s)tp-detail[^>]*>(.*?)</span>', frag)
    return {
        "core": one_line(c.group(1)) if c else "",
        "detail": one_line(d.group(1)) if d else "",
    }


def split_sections(h):
    """按 id="xxx" 把正文切成命名区块，返回 {id: html}。"""
    marks = []
    for m in re.finditer(r'<div[^>]*\bid="([a-z0-9-]+)"[^>]*>', h, re.I):
        marks.append((m.group(1), m.start()))
    out = {}
    for i, (name, pos) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(h)
        if name not in out:
            out[name] = h[pos:end]
    return out


# ================================================================ 翻译

def parse_translation(h):
    """翻译：中文原文 + 整篇参考译文 + 衔接/主旨/时态/译法 + 逐句解析。"""
    out = {"title": h1_text(h)}

    # 中文原文
    sm = re.search(r'(?s)<div[^>]*\bid="stem"[^>]*>(.*?)</div>', h)
    if sm:
        out["source_zh"] = to_text(sm.group(1))

    # 整篇参考译文（id 可能是 final / whole / translation）
    for key in ("final", "whole", "translation", "en"):
        fm = re.search(r'(?s)<div[^>]*\bid="' + key + r'"[^>]*>(.*?)</div>', h)
        if fm:
            t = to_text(fm.group(1))
            if t and len(t) > 40:
                out["reference_en"] = t
                break
    if "reference_en" not in out:
        # 兜底：整篇英译常放在 class 含 tp-final 或 reference 的块
        fm = re.search(r'(?s)<div[^>]*class="[^"]*(?:tp-ref|reference-en|tp-final-whole)[^"]*"[^>]*>(.*?)</div>', h)
        if fm:
            out["reference_en"] = to_text(fm.group(1))

    # 衔接
    cm = re.search(r'(?s)<div[^>]*\bid="cohesion"[^>]*>(.*?)</div>\s*</div>', h)
    if not cm:
        cm = re.search(r'(?s)【衔接】.*?<ul class="tp-list"[^>]*>(.*?)</ul>', h)
    if cm:
        links = []
        for lm in re.finditer(r'(?s)<li[^>]*>(.*?)</li>', cm.group(1)):
            pr = grab_tp_pair(lm.group(1))
            if pr["core"]:
                links.append(pr)
        if links:
            out["cohesion"] = links

    # 主旨 / 时态
    for name, pat in [("main_idea", "【主旨】"), ("tense", "【时态】")]:
        m = re.search(r'(?s)' + pat + r'.*?(<div class="rp-row[^"]*"[^>]*>.*?</div>)\s*(?=<div class="rp-row|</div>)', h)
        if m:
            pr = grab_tp_pair(m.group(1))
            if pr["core"]:
                out[name] = pr

    # 译法（专名/文化词统一译法）
    tm = re.search(r'(?s)【译法】.*?<ul class="tp-list"[^>]*>(.*?)</ul>', h)
    if tm:
        items = []
        for lm in re.finditer(r'(?s)<li[^>]*class="[^"]*tqp-chunk[^"]*"[^>]*>(.*?)</li>', tm.group(1)):
            pr = grab_tp_pair(lm.group(1))
            if pr["core"]:
                items.append(pr)
        if items:
            out["term_notes"] = items

    # 逐句解析
    units = []
    pm = re.search(r'(?s)<div[^>]*\bid="parsing"[^>]*>(.*)', h)
    if pm:
        body = pm.group(1)
        for um in re.finditer(r'<div[^>]*class="[^"]*\btqp-unit\b[^"]*"[^>]*>', body):
            sp = elem_span(body, um.start())
            if not sp:
                break
            item = body[um.start():sp[2]]
            zh = re.search(r'(?s)class="[^"]*tqp-stem[^"]*"[^>]*>(.*?)</div>', item)
            strat = re.search(r'(?s)class="[^"]*tqp-strategy[^"]*"[^>]*>(.*?)</div>', item)
            fin = re.search(r'(?s)class="[^"]*tqp-final[^"]*"[^>]*>(.*?)</div>', item)
            if zh or fin:
                units.append({
                    "zh": to_text(zh.group(1)) if zh else "",
                    "strategy": to_text(strat.group(1)) if strat else "",
                    "en": one_line(fin.group(1)) if fin else "",
                })
    if units:
        out["sentences"] = units

    return out


# ================================================================ 写作

def parse_writing(h):
    """写作：题目 + 范文 + 中译 + 逐段拆解。结构待实测，先用较宽的抓法。"""
    out = {"title": h1_text(h)}

    # Directions（题目要求）
    dm = re.search(r'(?s)Directions\s*[:：]?(.*?)(?=Part\s|$)', h)
    if dm:
        out["directions"] = to_text(dm.group(1))[:1500]

    # 范文：找含 wp- 前缀的类
    for cls in ("wp-sample", "wp-model", "wp-essay", "sample", "model-essay"):
        m = re.search(r'(?s)<div[^>]*class="[^"]*\b' + cls + r'\b[^"]*"[^>]*>(.*?)</div>', h)
        if m:
            t = to_text(m.group(1))
            if t:
                out["sample_en"] = t
                break

    # 兜底：抽所有 wp- 块
    wps = []
    for m in re.finditer(r'<div[^>]*class="[^"]*\bwp-([a-z-]+)\b[^"]*"[^>]*>', h):
        sp = elem_span(h, m.start())
        if sp:
            wps.append({"kind": m.group(1), "text": to_text(h[sp[0]:sp[1]])})
    if wps and "sample_en" not in out:
        out["blocks"] = wps

    return out


# ================================================================ 选词填空 / 长篇阅读

def parse_banked_cloze(h):
    """选词填空：文章（带空）+ 词库 + 逐空解析。

    实测结构（part3-section-a）：
      id="p-N"      带空短文段落，空号内联为 <u> 26 </u>；
                    段末有 <p class="lt-zh"> 中文翻译
      id="wordbank" 15 词词库，每项 <li class="wb__item">：
                    wb__letter(A) wb__word(affirmed) wb__pos(动词)
                    wb__gloss(肯定、证实) wb__used(用于第 30 空)
      id="q-NN"     逐空解析（下文沿用 rp-row 抽取）
    """
    out = {"title": h1_text(h)}

    # --- 带空短文：id="p-N"，空号保留为 __(NN)__ 占位符 ---
    paras = []
    seen_p = set()
    for m in re.finditer(r'id="p-(\d+)"', h):
        no = int(m.group(1))
        if no in seen_p:
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
        # 空号还原：<u> 26 </u> -> __(26)__
        en_part = re.sub(
            r'<u[^>]*>\s* ?(\d+) ?\s*</u>',
            lambda mm: ' __(%s)__ ' % mm.group(1),
            en_part,
        )
        en = one_line(en_part)
        if en or zh:
            seen_p.add(no)
            paras.append({"no": no, "en": en, "zh": zh})
    paras.sort(key=lambda x: x["no"])
    if paras:
        out["passages"] = paras

    # --- 词库：id="wordbank" 下的 li.wb__item ---
    bank = []
    wm = re.search(r'<[a-z0-9]+[^>]*\bid="wordbank"[^>]*>', h, re.I)
    if wm:
        wsp = elem_span(h, wm.start())
        wseg = h[wm.start():wsp[2]] if wsp else ""
        for m in re.finditer(r'<li[^>]*class="[^"]*\bwb__item\b[^"]*"[^>]*>', wseg):
            sp = elem_span(wseg, m.start())
            if not sp:
                break
            item = wseg[m.start():sp[2]]
            letter = re.search(r'wb__letter[^>]*>(.*?)</span>', item, re.S)
            word = re.search(r'wb__word[^>]*>(.*?)</span>', item, re.S)
            pos = re.search(r'wb__pos[^>]*>(.*?)</span>', item, re.S)
            gloss = re.search(r'wb__gloss[^>]*>(.*?)</p>', item, re.S)
            used = re.search(r'wb__used[^>]*>(.*?)</span>', item, re.S)
            used_no = 0
            if used:
                um = re.search(r'(\d+)', one_line(used.group(1)))
                if um:
                    used_no = int(um.group(1))
            L = one_line(letter.group(1)).strip(")） ") if letter else ""
            W = one_line(word.group(1)) if word else ""
            if not W:
                continue
            bank.append({
                "letter": L,
                "word": W,
                "pos": one_line(pos.group(1)) if pos else "",
                "gloss": one_line(gloss.group(1)) if gloss else "",
                "used": used_no,
                "idle": used_no == 0,
            })
    if bank:
        out["wordbank"] = bank

    pm = re.search(r'(?s)<div[^>]*\bid="parsing"[^>]*>(.*)', h)
    seg = pm.group(1) if pm else h

    # 逐空解析：rp-row 里带 【答案】 的行
    blanks = []
    for m in re.finditer(r'<div[^>]*class="[^"]*\brp-row\b[^"]*"[^>]*>', seg):
        sp = elem_span(seg, m.start())
        if not sp:
            break
        row = seg[m.start():sp[2]]
        tag = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
        if not tag:
            continue
        tn = one_line(tag.group(1)).strip("【】 ")
        body = one_line(row[tag.end():])
        if tn and body:
            blanks.append({"tag": tn, "text": body})
    if blanks:
        out["rows"] = blanks
    return out


def parse_long_reading(h):
    """长篇阅读（信息匹配）：文章段落 + 陈述句（题干）+ 每题解析。

    结构与仔细阅读一致：id=q-NN（题干中译）+ id=qp-NN（题干英文在 data-pdh-stem）。
    """
    out = {"title": h1_text(h)}

    # 文章段落：id="p-N"
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
    out["passages"] = paras

    # 陈述句（题干）：id=qp-NN，英文在 data-pdh-stem
    items = []
    for m in re.finditer(r'<div[^>]*\bid="qp-(\d+)"[^>]*>', h):
        no = int(m.group(1))
        sp = elem_span(h, m.start())
        if not sp:
            continue
        inner = h[sp[0]:sp[1]]
        sm = re.search(r'(?s)data-pdh-stem[^>]*>(.*?)</div>', inner)
        en = one_line(sm.group(1)) if sm else ""
        # 题干中译在容器外面
        tail = h[sp[2]: sp[2] + 3000]
        zm = re.search(r'(?s)<p[^>]*class="[^"]*lqp-stem[^"]*"[^>]*>(.*?)</p>', tail)
        zh = one_line(zm.group(1)) if zm else ""

        # 该句解析
        ana = {}
        am = re.search(r'<div class="rp-ana"[^>]*aria-label="第\s*' + str(no) + r'\s*句解析"[^>]*>', h)
        if am:
            asp = elem_span(h, am.start())
            seg = h[am.start():asp[2]] if asp else ""
            # 目标段号：优先从「答案」文字里提（如「出自 E 段」），
            # 再退回 rp-locate-p 锚点
            for rm in re.finditer(r'<div class="rp-row[^"]*"[^>]*>', seg):
                rsp = elem_span(seg, rm.start())
                if not rsp:
                    break
                row = seg[rm.start():rsp[2]]
                tg = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
                if not tg:
                    continue
                tn = one_line(tg.group(1)).strip("【】 ")
                body = one_line(row[tg.end():])
                if tn and body:
                    ana[tn] = body

            # 从「答案」文字里提目标段号：如「出自 E 段」「答案为 E」
            ans_txt = ana.get("答案", "")
            if ans_txt:
                pm = (re.search(r'出自\s*([A-Z]{1,2})\s*段', ans_txt)
                      or re.search(r'([A-Z]{1,2})\s*段', ans_txt)
                      or re.match(r'^\s*([A-Z]{1,2})\b', ans_txt))
                if pm:
                    ana["para"] = pm.group(1)
        items.append({"no": no, "en": en, "zh": zh, "analysis": ana})

    if items:
        out["statements"] = sorted(items, key=lambda x: x["no"])

    return out


# ================================================================ 入口

DISPATCH = {
    "part-iv": parse_translation,
    "part1": parse_writing,
    "part3-section-a": parse_banked_cloze,
    "part3-section-b": parse_long_reading,
}


def parse_file(path):
    name = os.path.splitext(os.path.basename(path))[0]
    fn = DISPATCH.get(name)
    if not fn:
        return {"error": "no parser for " + name}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    return fn(strip_scripts(raw))


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", "2022-06-1")
    for name in ["part-iv", "part1", "part3-section-a", "part3-section-b"]:
        p = os.path.join(base, name + ".html")
        print("=" * 74)
        print("FILE:", name)
        if not os.path.exists(p):
            print("  [缺失]")
            continue
        d = parse_file(p)
        print(json.dumps(d, ensure_ascii=False, indent=1)[:2600])
