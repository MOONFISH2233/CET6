# -*- coding: utf-8 -*-
"""分析 sections 解析页的 DOM 结构（解析器的基础）。"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def body_only(h):
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def show(path, n=1):
    p = os.path.join(RAW, path)
    if not os.path.exists(p):
        print(f"[缺失] {path}")
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        h = f.read()
    print("=" * 72)
    print(f"FILE: {path}   {len(h)} B")
    b = body_only(h)
    print(f"去脚本后: {len(b)} B")

    # class 频次
    cnt = {}
    for c in re.findall(r'class="([^"]+)"', b):
        for part in c.split():
            cnt[part] = cnt.get(part, 0) + 1
    print("  --- class top 40 ---")
    for k, v in sorted(cnt.items(), key=lambda x: -x[1])[:40]:
        print(f"    {v:>4}  {k}")

    return b


def outline(b, name):
    """打印 main/article 区域的标签骨架。"""
    print(f"\n  --- {name} 骨架（main/article 内，缩进式）---")
    m = re.search(r"(?s)<(main|article)\b.*?</\1>", b)
    if not m:
        print("    没找到 main/article，改用 body")
        m = re.search(r"(?s)<body\b.*?</body>", b)
    if not m:
        return
    seg = m.group(0)
    print(f"    区域长度: {len(seg)}")
    depth = 0
    out = []
    for t in re.finditer(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>", seg):
        close, tag, attrs = t.group(1), t.group(2).lower(), t.group(3)
        if tag in ("br", "img", "input", "hr", "meta", "link"):
            continue
        if close:
            depth = max(0, depth - 1)
            continue
        cls = ""
        cm = re.search(r'class="([^"]*)"', attrs)
        if cm:
            cls = "." + ".".join(cm.group(1).split()[:3])
        did = ""
        dm = re.search(r'(?:id|data-[a-z-]+)="([^"]*)"', attrs)
        if dm:
            did = "[" + dm.group(1)[:28] + "]"
        out.append("  " * depth + f"<{tag}{cls}{did}>")
        depth += 1
        if len(out) > 120:
            out.append("  " * depth + "... (截断)")
            break
    print("\n".join(out))


def main():
    for path, nm in [
        ("2024-06-1/part3-section-c-1.html", "仔细阅读C1"),
        ("2024-06-1/part-iv.html", "翻译"),
        ("2024-06-1/part1.html", "写作"),
    ]:
        b = show(path)
        if b:
            outline(b, nm)


if __name__ == "__main__":
    main()
