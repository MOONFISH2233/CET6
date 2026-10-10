# -*- coding: utf-8 -*-
"""摸清懒笔记页面的 HTML 结构，为写解析器探路。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def load(setname, page):
    p = os.path.join(RAW, setname, page + ".html")
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_scripts(h):
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def main():
    h = load("2024-06-1", "part3-section-c-1")
    print("原始长度:", len(h))

    print("\n=== class 名出现频次 top 60 ===")
    cls = re.findall(r'class="([^"]+)"', h)
    cnt = {}
    for c in cls:
        for part in c.split():
            cnt[part] = cnt.get(part, 0) + 1
    for k, v in sorted(cnt.items(), key=lambda x: -x[1])[:60]:
        print(f"  {v:>5}  {k}")

    print("\n=== 结构标签统计 ===")
    for tag in ["section", "article", "div", "p", "li", "details", "summary",
                "h1", "h2", "h3", "h4", "table", "tr", "td"]:
        n = len(re.findall(r"<" + tag + r"[\s>]", h))
        if n:
            print(f"  <{tag}> {n}")

    print("\n=== 找含「答案」的元素上下文（前 5 处）===")
    body = strip_scripts(h)
    for i, m in enumerate(re.finditer("答案", body)):
        if i >= 5:
            break
        s = max(0, m.start() - 350)
        seg = body[s:m.start() + 150]
        seg = re.sub(r"\s+", " ", seg)
        print(f"\n  --- 第 {i+1} 处 ---")
        print("  " + seg[-450:])

    print("\n\n=== 找「判型/拆句/定位/选项」标记的标签（前 3 处）===")
    for i, m in enumerate(re.finditer("判型", body)):
        if i >= 3:
            break
        s = max(0, m.start() - 500)
        seg = body[s:m.start() + 100]
        seg = re.sub(r"\s+", " ", seg)
        print(f"\n  --- 第 {i+1} 处 ---")
        print("  " + seg[-600:])


if __name__ == "__main__":
    main()
