# -*- coding: utf-8 -*-
"""精确看正文区域 HTML（阅读/翻译/写作/选词），为解析器定锚点。"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def load(path):
    with open(os.path.join(RAW, path), "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def body_only(h):
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def show_around(h, anchor, before=200, after=2200, label=""):
    i = h.find(anchor)
    if i < 0:
        print(f"  [{label}] 找不到锚点 {anchor!r}")
        return
    seg = h[max(0, i - before): i + after]
    print(f"\n  ==== [{label}] 锚点 {anchor!r} @ {i} ====")
    print(seg)


print("#" * 76)
print("# 阅读 C1")
print("#" * 76)
h = body_only(load("2022-06-1/part3-section-c-1.html"))
# 找正文起点：第一篇文章标记
for a in ['id="p-1"', 'data-ptoc-link="p-1"', 'Passage One', 'P1', 'rp-text', 'id="q-46"']:
    i = h.find(a)
    print(f"  锚点 {a!r} -> {i}")
show_around(h, 'id="p-1"', 300, 1800, "阅读正文段P1")
show_around(h, 'rp-verdict', 800, 1500, "阅读逐题解析")

print()
print("#" * 76)
print("# 翻译")
print("#" * 76)
h = body_only(load("2022-06-1/part-iv.html"))
for a in ['id="stem"', 'id="final"', 'tp-core', 'tqp-unit', 'id="q-1"', 'tqp-chunk']:
    i = h.find(a)
    print(f"  锚点 {a!r} -> {i}")
show_around(h, 'tp-core', 300, 2000, "翻译正文")

print()
print("#" * 76)
print("# 写作")
print("#" * 76)
h = body_only(load("2022-06-1/part1.html"))
for a in ['Directions', 'sample', 'model', 'essay', 'wp-', '范文']:
    print(f"  锚点 {a!r} -> {h.find(a)}")
