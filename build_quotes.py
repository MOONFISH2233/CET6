# -*- coding: utf-8 -*-
"""
把 美工/*.md 里的温柔台词解析成 quotes.json，供站点做「每日一句」。

源文件（D:\\学习\\六级\\美工\\）结构：`# 标题` + 前言 `>` 块 + `## 小标题` + `> 引文` + `---`。
注意：这些 md 里后半段混进了别的内容（别的文件的副本、PowerShell 残句、对话残句），
所以这里：① 只认 `##`/`###` 段落里的 `>` 引文；② 跨文件按正文去重；③ 过滤明显的垃圾行；
④ 出处靠小标题推（`角色 · 作品`），推不出来的用文件默认作者。

输出：data/quotes.json → 拷到 site/assets/quotes.json
  [{"t": "正文", "a": "作者/角色", "s": "作品", "f": "来源文件"}]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(os.path.dirname(HERE), "美工")
DATA = os.path.join(HERE, "data")
SITE = os.path.join(HERE, "site")

# 文件名 -> (默认作者, 默认作品)
FILES = [
    ("蒲熠星-台词合集.md", "蒲熠星", ""),
    ("孙路路-台词合集.md", "孙路路", ""),
    ("温迪-台词合集.md", "温迪", "原神"),
    ("原神-温柔动人台词.md", "原神", "原神"),
    ("原神-台词合集.md", "温迪", "原神"),
]

# 小标题里出现这些词就不是人名，是分类名
NOT_A_NAME = ("关于", "诗歌", "语音", "其他", "精选", "说明", "介绍", "角色",
              "最核心", "温柔", "勇气", "旅途", "时间", "自由", "行动", "遗憾",
              "待补充", "用法", "收录", "配色", "图片", "建议", "全部", "附录",
              "佳酿节", "之歌", "节庆")

# 混进来的垃圾：PowerShell、对话残句、元信息
JUNK = ("write-output", "get-childitem", "```", "重写完了", "先纠正我上一条",
        "用途：", "收录标准", "来源：", "搭配图片", "配色建议", "待补充",
        "$", "**", "http://", "https://")


def is_junk(t):
    low = t.lower()
    if len(t) < 4 or len(t) > 220:
        return True
    for j in JUNK:
        if j in low:
            return True
    # 对话残句：带「我」且像在说整理过程
    if re.search(r"(我上一条|我说错|整理完|已经改好|这条删)", t):
        return True
    return False


def parse_heading(h, default_author, default_work):
    """从 `## 八、诗歌 ·《时与风》` / `## 那维莱特 · 枫丹最高审判官` 推 (作者, 作品)。

    分隔符只认「空格 + ·」（`温迪（风神·巴巴托斯）` 里那个 · 在括号内，不是分隔符）。
    """
    h = h.strip()
    h = re.sub(r"^[一二三四五六七八九十百零\d]+[、.．]\s*", "", h)   # 去掉「八、」
    author, work = default_author, default_work
    if re.search(r"\s·", h):
        first, rest = [x.strip() for x in re.split(r"\s·", h, 1)]
        if first and len(first) <= 8 and not any(k in first for k in NOT_A_NAME):
            author = first
        m = re.search(r"《([^》]+)》", rest or h)
        if m:
            work = m.group(1)
    else:
        m = re.search(r"《([^》]+)》", h)
        if m:
            work = m.group(1)
    return author, work


def parse_file(path, default_author, default_work):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")
    author, work = default_author, default_work
    seen_section = False
    seen_h1 = False
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        # 第二个一级标题 = 后面粘了别的文件的副本（这几个 md 都这样），到此为止
        if re.match(r"^#\s+\S", ln):
            if seen_h1:
                break
            seen_h1 = True
            i += 1
            continue
        m = re.match(r"^#{2,4}\s+(.*)$", ln)
        if m:
            seen_section = True
            author, work = parse_heading(m.group(1), default_author, default_work)
            i += 1
            continue
        if ln.startswith(">") and seen_section:      # 只有进了正文段落才收
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            t = "\n".join(x for x in buf if x)
            t = re.sub(r"\s*★\s*$", "", t).strip()
            if t and not is_junk(t):
                out.append({"t": t, "a": author, "s": work})
            continue
        i += 1
    return out


def main():
    quotes, seen = [], set()
    for fn, da, dw in FILES:
        p = os.path.join(ART, fn)
        if not os.path.exists(p):
            print("缺文件:", p)
            continue
        got = parse_file(p, da, dw)
        new = 0
        for q in got:
            key = re.sub(r"\s+", "", q["t"])
            if key in seen:
                continue
            seen.add(key)
            q["f"] = fn
            quotes.append(q)
            new += 1
        print("  %-26s 解析 %3d 条 · 新增 %3d" % (fn, len(got), new))

    # 短句被长句包含 = 同一句的「精简版」（原神-台词合集.md 是精简版），只留长的
    norm = [re.sub(r"\s+", "", q["t"]) for q in quotes]
    keep = []
    for i, q in enumerate(quotes):
        a = norm[i]
        if any(a != norm[j] and a in norm[j] for j in range(len(quotes))):
            continue
        keep.append(q)
    dropped = len(quotes) - len(keep)
    quotes = keep

    dst = os.path.join(DATA, "quotes.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=1)
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "assets", "quotes.json"), "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, separators=(",", ":"))

    by = {}
    for q in quotes:
        by[q["a"]] = by.get(q["a"], 0) + 1
    print("\n合计 %d 条（去掉 %d 条精简重复）· data/quotes.json %.1f KB"
          % (len(quotes), dropped, os.path.getsize(dst) / 1024))
    print("按作者:", "、".join("%s %d" % (a, n) for a, n in sorted(by.items(), key=lambda x: -x[1])))
    print("\n抽查（前 12 条）:")
    for q in quotes[:12]:
        src = " ·《%s》" % q["s"] if q["s"] else ""
        print("  ——%s%s ｜ %s" % (q["a"], src, q["t"].replace("\n", " / ")[:52]))
    longest = sorted(quotes, key=lambda q: -len(q["t"]))[:3]
    print("\n最长的 3 条（看看要不要截）:")
    for q in longest:
        print("  %3d 字 ｜ %s…" % (len(q["t"]), q["t"][:40].replace("\n", " ")))


if __name__ == "__main__":
    main()
