# -*- coding: utf-8 -*-
"""
翻译（汉译英 Part IV）解析器。

页面结构（实测，全部靠 id 定位）：
  <div id="directions">  作答说明
  <div id="stem">        中文原文（整段）
  <div id="translation"> 整篇参考英译定稿
  <div id="cohesion">    【衔接】若干条：<strong class="tp-core">标题</strong>
                              <span class="tp-detail">说明</span>
  <div id="parsing">     逐句解析区
     <div id="global">   【主旨】/【时态】/【译法】
        <div class="rp-row"><span class="rp-tag">【主旨】</span>
           <p class="rp-text"><strong class="tp-core">…</strong>
              <span class="tp-detail">…</span></p></div>
        <div class="rp-row rp-row--chunks"><span class="rp-tag">【译法】</span>
           <ul class="tp-list">
             <li class="tqp-chunk"><strong class="tp-core">词</strong>
                 <span class="tp-detail">说明</span></li>
     <div id="s-1"> … <div id="s-2"> …    每个句子单元
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_lib import strip_scripts, to_text, one_line, elem_span, h1_text  # noqa: E402


def block_by_id(h, name):
    """取 id=name 的 div 的内容 HTML（不含自身标签）。"""
    m = re.search(r'<div[^>]*\bid="' + re.escape(name) + r'"[^>]*>', h)
    if not m:
        return ""
    sp = elem_span(h, m.start())
    return h[sp[0]:sp[1]] if sp else ""


def tp_pair(frag):
    """取 tp-core / tp-detail 配对。"""
    c = re.search(r'(?s)tp-core[^>]*>(.*?)</strong>', frag)
    d = re.search(r'(?s)tp-detail[^>]*>(.*?)</span>', frag)
    return {
        "core": one_line(c.group(1)) if c else "",
        "detail": one_line(d.group(1)) if d else "",
    }


def parse_translation(h):
    out = {"title": h1_text(h)}

    # Directions
    d = block_by_id(h, "directions")
    if d:
        out["directions"] = to_text(d)

    # 中文原文
    s = block_by_id(h, "stem")
    if s:
        out["source_zh"] = to_text(s)

    # 参考译文
    t = block_by_id(h, "translation")
    if t:
        txt = to_text(t)
        # 去掉开头的说明行（“整篇参考英译是复盘资产…”那句）
        lines = [ln for ln in txt.split("\n") if ln]
        keep = []
        for ln in lines:
            if ln.startswith("整篇参考英译") or ln.startswith("参考译文"):
                continue
            keep.append(ln)
        out["reference_en"] = "\n".join(keep)

    # 衔接
    c = block_by_id(h, "cohesion")
    if c:
        items = []
        for lm in re.finditer(r'(?s)<li[^>]*>(.*?)</li>', c):
            pr = tp_pair(lm.group(1))
            if pr["core"]:
                items.append(pr)
        if items:
            out["cohesion"] = items

    # 主旨 / 时态 / 译法（都在 id=global 里）
    g = block_by_id(h, "global")
    if g:
        # 按 rp-row 切
        for m in re.finditer(r'<div class="rp-row[^"]*"[^>]*>', g):
            sp = elem_span(g, m.start())
            if not sp:
                break
            row = g[m.start():sp[2]]
            tag = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
            if not tag:
                continue
            tn = one_line(tag.group(1)).strip("【】 ")
            if tn == "主旨":
                out["main_idea"] = tp_pair(row)
            elif tn == "时态":
                out["tense"] = tp_pair(row)
            elif tn == "译法":
                items = []
                for lm in re.finditer(r'(?s)<li[^>]*class="[^"]*tqp-chunk[^"]*"[^>]*>(.*?)</li>', row):
                    pr = tp_pair(lm.group(1))
                    if pr["core"]:
                        items.append(pr)
                if items:
                    out["term_notes"] = items

    # 逐句解析：id=s-1, s-2, ...
    sentences = []
    for m in re.finditer(r'<div[^>]*\bid="s-(\d+)"[^>]*>', h):
        no = int(m.group(1))
        sp = elem_span(h, m.start())
        if not sp:
            continue
        item = h[sp[0]:sp[1]]
        # 中文句
        zh = ""
        zm = re.search(r'(?s)<div[^>]*class="[^"]*tqp-stem[^"]*"[^>]*>(.*?)</div>', item)
        if zm:
            zh = to_text(zm.group(1))
        # 策略（可能有多个 rp-row）
        strat = []
        for sm in re.finditer(r'<div class="rp-row[^"]*"[^>]*>', item):
            ssp = elem_span(item, sm.start())
            if not ssp:
                break
            row = item[sm.start():ssp[2]]
            tg = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
            if tg:
                tn = one_line(tg.group(1)).strip("【】 ")
                body = one_line(row[tg.end():])
                if tn and body:
                    strat.append({"tag": tn, "text": body})
        # 定稿英译
        en = ""
        em = re.search(r'(?s)<div[^>]*class="[^"]*tqp-final[^"]*"[^>]*>(.*?)</div>', item)
        if em:
            en = one_line(em.group(1))
        sentences.append({"no": no, "zh": zh, "steps": strat, "en": en})

    if sentences:
        out["sentences"] = sorted(sentences, key=lambda x: x["no"])

    return out


def parse_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    return parse_translation(strip_scripts(raw))


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "raw", "2022-06-1", "part-iv.html")
    d = parse_file(p)
    print("标题:", d["title"])
    print("\n中文原文:", d.get("source_zh", "")[:150])
    print("\n参考译文:", d.get("reference_en", "")[:260])
    print("\n衔接:", len(d.get("cohesion", [])), "条")
    for c in d.get("cohesion", [])[:1]:
        print(f"   {c['core']}")
        print(f"     {c['detail'][:80]}")
    print("\n主旨:", json.dumps(d.get("main_idea"), ensure_ascii=False)[:150])
    print("时态:", json.dumps(d.get("tense"), ensure_ascii=False)[:150])
    print(f"\n译法: {len(d.get('term_notes', []))} 条")
    for t in d.get("term_notes", [])[:2]:
        print(f"   {t['core']}: {t['detail'][:60]}")
    print(f"\n逐句: {len(d.get('sentences', []))} 句")
    for s in d.get("sentences", [])[:2]:
        print(f"   [{s['no']}] {s['zh'][:60]}")
        for st in s["steps"]:
            print(f"        【{st['tag']}】{st['text'][:70]}")
        print(f"        → {s['en'][:90]}")
