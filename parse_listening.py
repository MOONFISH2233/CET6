# -*- coding: utf-8 -*-
"""
听力（Part II）解析器。

页面结构（实测）：

  录音文字稿（每篇一个）：
   <div id="lt-1">
     <div class="lt-piece-head">
       <span>Questions 1 to 4 are based on the conversation...</span>
       <button class="lt-listen" data-listen-seek="43.266">播放本篇</button>
     <div class="lt-body">
       <p id="p-1-1" class="lt-en">1 W: ...英文...</p>
       <p class="lt-zh">W: ...中译...</p>
       <p id="p-1-2" class="lt-en">2 M: ...</p>
       <p class="lt-zh">M: ...</p>
       ...

  题目（每题一个）：
   <div id="qp-1" class="exam-q">
     <div>1.</div>
     <span data-pdh-letter="A">选项A</span> ... B/C/D
   <div class="rp-ana" aria-label="第 1 题解析">
     <div class="rp-row"><span class="rp-tag">【题目】</span>
        <p class="rp-stem-en" data-pdh-stem>题干英文</p></div>
     <div class="rp-row"><span class="rp-tag">【翻译】</span>
        <div class="lqp-trans">
          <p class="lqp-trans-stem">题干中译</p>
          <ul class="lqp-trans-choices">
            <li><span class="lqp-trans-letter">A)</span> 选项A中译</li> ...
     <div class="rp-row"><span class="rp-tag">【答案】</span>
        <strong class="rp-ans">D</strong><span class="rp-qtype">（细节题）</span>
     <div class="rp-row"><span class="rp-tag">【定位】</span>
        <p class="rp-locate-en">定位英文</p><p class="rp-locate-zh">定位中译</p>
     <div class="rp-row"><span class="rp-tag">【信号】</span>...
     <div class="rp-row"><span class="rp-tag">【替换】</span>...
     <div class="rp-row"><span class="rp-tag">【排除】</span>...

  Section 分节：<div id="section-a"> / id="section-b" / id="section-c"
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_lib import strip_scripts, to_text, one_line, elem_span, h1_text  # noqa: E402


# ------------------------------------------------------------ 录音文字稿

def parse_transcripts(h):
    """抽 lt-N 篇目：标题 + 起播秒数 + 逐句（英文/中译交替）。"""
    pieces = []
    for m in re.finditer(r'<div[^>]*\bid="lt-(\d+)"[^>]*>', h):
        no = int(m.group(1))
        sp = elem_span(h, m.start())
        if not sp:
            continue
        item = h[sp[0]:sp[1]]

        head = ""
        hm = re.search(r'(?s)lt-piece-head.*?<span>(.*?)</span>', item)
        if hm:
            head = one_line(hm.group(1))
        seek = ""
        sm = re.search(r'data-listen-seek="([\d.]+)"', item)
        if sm:
            seek = sm.group(1)

        # 逐句：p-N-M（英文）与紧跟的 lt-zh（中译）
        lines = []
        for pm in re.finditer(r'<p[^>]*\bid="p-' + str(no) + r'-(\d+)"[^>]*class="([^"]*)"[^>]*>(.*?)</p>', item, re.S):
            idx = int(pm.group(1))
            cls = pm.group(2)
            body = pm.group(3)
            # 去掉句内编号 span
            body = re.sub(r'(?s)<span[^>]*class="[^"]*exam-pno[^"]*"[^>]*>.*?</span>', '', body)
            en = one_line(body) if "lt-en" in cls else ""
            lines.append({"idx": idx, "en": en, "zh": ""})
        # 中译行（没有 id，靠 class lt-zh 顺序对齐）
        zh_list = []
        for zm in re.finditer(r'<p[^>]*class="[^"]*\blt-zh\b[^"]*"[^>]*>(.*?)</p>', item, re.S):
            zh_list.append(one_line(zm.group(1)))
        for i, ln in enumerate(lines):
            if i < len(zh_list):
                ln["zh"] = zh_list[i]

        pieces.append({"no": no, "head": head, "seek": seek, "lines": lines})

    pieces.sort(key=lambda x: x["no"])
    return pieces


# ------------------------------------------------------------ 题目 + 解析

def parse_question(h, no):
    """抽第 no 题：选项 + 解析。"""
    q = {"no": no}

    # 选项（在 qp-N 里）
    opts = []
    m = re.search(r'<div[^>]*\bid="qp-' + str(no) + r'"[^>]*>', h)
    if m:
        sp = elem_span(h, m.start())
        if sp:
            inner = h[sp[0]:sp[1]]
            for om in re.finditer(r'(?s)data-pdh-letter="([A-D])"[^>]*>(.*?)</span>', inner):
                opts.append({"letter": om.group(1), "text": one_line(om.group(2)), "zh": ""})

    # 解析块
    am = re.search(r'<div class="rp-ana"[^>]*aria-label="第\s*' + str(no) + r'\s*题解析"[^>]*>', h)
    if am:
        asp = elem_span(h, am.start())
        seg = h[am.start():asp[2]] if asp else ""

        # 题干
        sm = re.search(r'(?s)data-pdh-stem[^>]*>(.*?)</p>', seg)
        if sm:
            q["stem"] = one_line(sm.group(1))

        # 翻译（题干中译 + 选项中译）
        zsm = re.search(r'(?s)class="lqp-trans-stem"[^>]*>(.*?)</p>', seg)
        if zsm:
            q["stem_zh"] = one_line(zsm.group(1))
        um = re.search(r'(?s)<ul[^>]*class="[^"]*lqp-trans-choices[^"]*"[^>]*>(.*?)</ul>', seg)
        if um:
            zh_map = {}
            for lm in re.finditer(r'(?s)<li[^>]*>(.*?)</li>', um.group(1)):
                seg2 = lm.group(1)
                lm2 = re.search(r'lqp-trans-letter[^>]*>\s*([A-D])', seg2)
                if lm2:
                    body = re.sub(r'(?s)<span[^>]*class="[^"]*lqp-trans-letter[^"]*"[^>]*>.*?</span>', '', seg2)
                    zh_map[lm2.group(1)] = one_line(body)
            for o in opts:
                o["zh"] = zh_map.get(o["letter"], "")

        # 答案 + 题型
        ansm = re.search(r'(?s)class="rp-ans"[^>]*>(.*?)</strong>', seg)
        if ansm:
            q["answer"] = one_line(ansm.group(1))
        tpm = re.search(r'(?s)class="rp-qtype"[^>]*>(.*?)</span>', seg)
        if tpm:
            q["qtype"] = one_line(tpm.group(1))

        # 各 【xx】 行
        for rm in re.finditer(r'<div class="rp-row[^"]*"[^>]*>', seg):
            rsp = elem_span(seg, rm.start())
            if not rsp:
                break
            row = seg[rm.start():rsp[2]]
            tg = re.search(r'rp-tag[^>]*>(.*?)</span>', row, re.S)
            if not tg:
                continue
            tn = one_line(tg.group(1)).strip("【】 ")
            if tn in ("题目", "翻译", "答案"):
                continue
            body = one_line(row[tg.end():])
            if tn and body:
                q.setdefault("analysis", {})[tn] = body

        # 定位结构化
        loc = {}
        en = re.search(r'(?s)class="rp-locate-en"[^>]*>(.*?)</p>', seg)
        zh = re.search(r'(?s)class="rp-locate-zh"[^>]*>(.*?)</p>', seg)
        if en or zh:
            loc["en"] = one_line(en.group(1)) if en else ""
            loc["zh"] = one_line(zh.group(1)) if zh else ""
            q["locate"] = loc

        # 选项逐个分析（若有）
        oa = []
        um2 = re.search(r'(?s)<ul class="rp-verdicts"[^>]*>(.*)', seg)
        if um2:
            body = um2.group(1)
            for li_m in re.finditer(r'<li[^>]*class="([^"]*\brp-verdict\b[^"]*)"[^>]*>', body):
                sp2 = elem_span(body, li_m.start())
                if not sp2:
                    break
                item = body[li_m.start():sp2[2]]
                lt = re.search(r'rp-verdict-letter[^>]*>\s*([A-D])', item)
                fl = re.search(r'(?s)rp-flag[^>]*>(.*?)</span>', item)
                nt = re.search(r'(?s)rp-verdict-note[^>]*>(.*?)</p>', item)
                rs = re.search(r'(?s)rp-verdict-reason[^>]*>(.*?)</', item)
                pairs = []
                for pm in re.finditer(r'(?s)<li class="rp-pair"[^>]*>(.*?)</li>', item):
                    ps = pm.group(1)
                    o1 = re.search(r'(?s)rp-pair-orig[^>]*>(.*?)</span>', ps)
                    o2 = re.search(r'(?s)rp-pair-opt[^>]*>(.*?)</span>', ps)
                    if o1 and o2:
                        pairs.append({"orig": one_line(o1.group(1)), "opt": one_line(o2.group(1))})
                oa.append({
                    "letter": lt.group(1) if lt else "",
                    "correct": "is-ok" in li_m.group(1),
                    "flag": one_line(fl.group(1)) if fl else "",
                    "note": one_line(nt.group(1)) if nt else "",
                    "reason": one_line(rs.group(1)) if rs else "",
                    "pairs": pairs,
                })
            if oa:
                oa.sort(key=lambda x: x["letter"])
                q["option_analysis"] = oa

    q["options"] = opts
    return q


def parse_sections(h):
    """抽 Section 分节：id=section-a/b/c 及其题号范围。"""
    secs = []
    for m in re.finditer(r'<div[^>]*\bid="section-([abc])"[^>]*>', h):
        letter = m.group(1).upper()
        sp = elem_span(h, m.start())
        seg = h[m.start():sp[2]] if sp else ""
        nums = [int(x) for x in re.findall(r'\bid="q-(\d+)"', seg)]
        secs.append({"section": letter, "from": min(nums) if nums else 0,
                     "to": max(nums) if nums else 0, "count": len(nums)})
    return secs


# ------------------------------------------------------------ 入口

def parse_listening(h):
    out = {"title": h1_text(h)}

    # 卷首 Directions
    dm = re.search(r'(?s)Directions\s*[:：](.*?)(?=<div id="section-|Part\s+II)', h)
    if dm:
        out["directions"] = to_text(dm.group(1))[:800]

    out["sections"] = parse_sections(h)
    out["transcripts"] = parse_transcripts(h)

    qs = []
    for m in re.finditer(r'<div[^>]*\bid="q-(\d+)"[^>]*>', h):
        no = int(m.group(1))
        qs.append(parse_question(h, no))
    seen = set()
    uniq = []
    for q in qs:
        if q["no"] in seen:
            continue
        seen.add(q["no"])
        uniq.append(q)
    out["questions"] = sorted(uniq, key=lambda x: x["no"])

    return out


def parse_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    return parse_listening(strip_scripts(raw))


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "raw", "2022-06-1", "listening.html")
    d = parse_file(p)
    print("标题:", d["title"])
    print("Section:", json.dumps(d["sections"], ensure_ascii=False))
    print(f"录音篇目: {len(d['transcripts'])}   题目: {len(d['questions'])}")
    print("\n--- 录音第 1 篇 ---")
    t = d["transcripts"][0]
    print(f"  head: {t['head'][:70]}")
    print(f"  seek: {t['seek']}  句数: {len(t['lines'])}")
    for ln in t["lines"][:2]:
        print(f"    [{ln['idx']}] {ln['en'][:85]}")
        print(f"         {ln['zh'][:70]}")
    print("\n--- 第 1 题 ---")
    q = d["questions"][0]
    print(f"  题干: {q.get('stem','')}")
    print(f"  中译: {q.get('stem_zh','')}")
    for o in q.get("options", []):
        print(f"  {o['letter']}) {o['text']}   | {o['zh']}")
    print(f"  答案: {q.get('answer')} {q.get('qtype','')}")
    print(f"  定位: {q.get('locate',{}).get('en','')[:90]}")
    print(f"  解析标签: {list(q.get('analysis',{}).keys())}")
    for k, v in q.get("analysis", {}).items():
        print(f"    【{k}】{v[:95]}")
    if q.get("option_analysis"):
        print("  选项分析:")
        for o in q["option_analysis"]:
            mk = "✓" if o["correct"] else " "
            print(f"    {mk} {o['letter']}) {o['flag']}  {o['note'][:60]}")
