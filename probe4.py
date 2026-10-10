# -*- coding: utf-8 -*-
"""分析 sections 解析页的 DOM 骨架，为解析器探路。"""
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def body_only(h):
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def classes(h, top=45):
    cnt = {}
    for c in re.findall(r'class="([^"]+)"', h):
        for p in c.split():
            cnt[p] = cnt.get(p, 0) + 1
    return sorted(cnt.items(), key=lambda x: -x[1])[:top]


def outline(h, name, maxlines=140):
    print(f"\n  --- {name} 骨架 ---")
    m = re.search(r"(?s)<(main|article)\b.*?</\1>", h)
    if not m:
        print("    ! 无 main/article，用 body")
        m = re.search(r"(?s)<body\b.*?</body>", h)
    if not m:
        return
    seg = m.group(0)
    print(f"    区域 {len(seg)} B")
    depth = 0
    out = []
    for t in re.finditer(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>", seg):
        close, tag, attrs = t.group(1), t.group(2).lower(), t.group(3)
        if tag in ("br", "img", "input", "hr", "meta", "link", "path", "svg"):
            continue
        if close:
            depth = max(0, depth - 1)
            continue
        cls = ""
        cm = re.search(r'class="([^"]*)"', attrs)
        if cm:
            cls = "." + ".".join(cm.group(1).split()[:2])
        extra = ""
        for a in ("data-pd-kind", "data-pd-no", "data-ptoc-link", "data-block", "id"):
            am = re.search(a + r'="([^"]*)"', attrs)
            if am:
                extra = f"[{a.split('-')[-1]}={am.group(1)[:18]}]"
                break
        out.append("  " * depth + f"<{tag}{cls}{extra}>")
        depth += 1
        if len(out) >= maxlines:
            out.append("  " * depth + "... (截断)")
            break
    print("\n".join(out))


def main():
    for path, nm in [
        ("2022-06-1/part3-section-c-1.html", "仔细阅读C1"),
        ("2022-06-1/part-iv.html", "翻译"),
        ("2022-06-1/part1.html", "写作"),
        ("2022-06-1/part3-section-a.html", "选词填空"),
    ]:
        p = os.path.join(RAW, path)
        if not os.path.exists(p):
            print(f"[缺失] {path}")
            continue
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            h = f.read()
        b = body_only(h)
        print("=" * 74)
        print(f"FILE: {path}  raw={len(h)}B  body={len(b)}B")
        print("  --- class top ---")
        for k, v in classes(b):
            print(f"    {v:>4}  {k}")
        outline(b, nm)


if __name__ == "__main__":
    main()
