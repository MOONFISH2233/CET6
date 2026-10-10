# -*- coding: utf-8 -*-
"""找骨架页里的数据线索：script 里的 URL / JSON / fetch 调用。"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


for page in ["part3-section-c-1", "part-iv", "listening", "part1"]:
    p = os.path.join(RAW, "2024-06-1", page + ".html")
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        h = f.read()
    print("=" * 70)
    print(f"PAGE: {page}   len={len(h)}")

    # 所有 script 标签内容
    scripts = re.findall(r"(?s)<script([^>]*)>(.*?)</script>", h)
    print(f"  script 数: {len(scripts)}")
    for i, (attrs, body) in enumerate(scripts):
        b = body.strip()
        a = attrs.strip()
        if not b and not a:
            continue
        print(f"  --- script[{i}] attrs={a[:160]!r} len={len(b)}")
        if b:
            print("      " + b[:800].replace("\n", "\n      "))

    # 找可能的接口路径 / json 文件名
    print("  --- 候选数据路径 ---")
    pats = set()
    for m in re.finditer(r'["\']([^"\']*\.(?:json|js))["\']', h):
        pats.add(m.group(1))
    for m in re.finditer(r'(/api/[^"\'\s<>)]+)', h):
        pats.add(m.group(1))
    for m in re.finditer(r'data-[a-z-]+="([^"]{0,120})"', h):
        pass
    for x in sorted(pats)[:30]:
        print("    " + x)

    # 找 data-* 属性（可能藏 id）
    print("  --- data-* 属性样本 ---")
    das = {}
    for m in re.finditer(r'data-([a-z-]+)="([^"]*)"', h):
        k = m.group(1)
        das.setdefault(k, []).append(m.group(2))
    for k, vs in sorted(das.items())[:25]:
        print(f"    data-{k}: {vs[:3]}")
