# -*- coding: utf-8 -*-
"""
汇总所有解析页里的「真题高频词」表，构建全局词库。

输出 data/dict.json：
  {
    "words": {
       "antibiotic": {"cefr":"B2", "gloss":"n. 抗生素", "freq":142, "papers":["2022-06-1",...]},
       ...
    },
    "meta": {"total": N, "source": "..."}
  }

同时输出每个套次自己的词表 data/hfw/<set>.json，供模块页底部的重点词块用。
词表里每个词带 mods 字段（该词出自哪几个模块页），模块页据此只显示本篇的词。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parse_lib import strip_scripts, parse_hfw  # noqa: E402
import build_data  # noqa: E402

RAW = os.path.join(HERE, "raw")
DATA = os.path.join(HERE, "data")

# raw 文件名 -> 模块 key 的唯一映射在 build_data.MODULES，这里复用
MOD_ORDER = [key for key, _, _ in build_data.MODULES]
PAGE_MODULE = {fn: key for key, fn, _ in build_data.MODULES}


# 英语词形还原（够用的规则版）
def lemmas(w):
    """给一个词，返回可能的原形候选（含自身）。"""
    w = w.lower()
    out = [w]
    if len(w) <= 3:
        return out
    # 复数 / 三单
    if w.endswith("ies") and len(w) > 4:
        out.append(w[:-3] + "y")
    if w.endswith("es") and len(w) > 3:
        out.append(w[:-2])
    if w.endswith("s") and not w.endswith("ss"):
        out.append(w[:-1])
    # 过去式 / 过去分词
    if w.endswith("ied") and len(w) > 4:
        out.append(w[:-3] + "y")
    if w.endswith("ed") and len(w) > 3:
        out.append(w[:-2])
        out.append(w[:-1])
        if len(w) > 4 and w[-3] == w[-4]:
            out.append(w[:-3])
    # 现在分词
    if w.endswith("ing") and len(w) > 4:
        out.append(w[:-3])
        out.append(w[:-3] + "e")
        if len(w) > 5 and w[-4] == w[-5]:
            out.append(w[:-4])
    # 比较级 / 最高级
    if w.endswith("er") and len(w) > 4:
        out.append(w[:-2])
        out.append(w[:-1])
    if w.endswith("est") and len(w) > 5:
        out.append(w[:-3])
        out.append(w[:-2])
    # 副词
    if w.endswith("ly") and len(w) > 4:
        out.append(w[:-2])
    return list(dict.fromkeys(out))


def main():
    os.makedirs(os.path.join(DATA, "hfw"), exist_ok=True)

    words = {}
    per_set = {}
    n_pages = 0

    for setname in sorted(os.listdir(RAW)):
        d = os.path.join(RAW, setname)
        if not os.path.isdir(d):
            continue
        merged = {}
        for fn in os.listdir(d):
            if not fn.endswith(".html"):
                continue
            p = os.path.join(d, fn)
            try:
                h = strip_scripts(open(p, encoding="utf-8", errors="replace").read())
            except Exception:
                continue
            ws = parse_hfw(h)
            if not ws:
                continue
            n_pages += 1
            mod = PAGE_MODULE.get(fn[:-5], "")
            for w in ws:
                k = w["word"].lower()
                # 该套内合并（同词取最大频次、保留最完整的 gloss、记下来自哪些模块）
                if k in merged:
                    m = merged[k]
                    m["in_paper"] = max(m["in_paper"], w["in_paper"])
                    if len(w["gloss"]) > len(m["gloss"]):
                        m["gloss"] = w["gloss"]
                    if mod and mod not in m["mods"]:
                        m["mods"].append(mod)
                else:
                    merged[k] = dict(w)
                    merged[k]["mods"] = [mod] if mod else []

                # 全局合并
                if k in words:
                    g = words[k]
                    g["freq"] += w["in_paper"]
                    g["exam"] = max(g["exam"], w["in_exam"])
                    if not g["gloss"] and w["gloss"]:
                        g["gloss"] = w["gloss"]
                    if setname not in g["papers"]:
                        g["papers"].append(setname)
                else:
                    words[k] = {
                        "cefr": w["cefr"],
                        "gloss": w["gloss"],
                        "freq": w["in_paper"],
                        "exam": w["in_exam"],
                        "papers": [setname],
                    }

        if merged:
            for m in merged.values():
                m["mods"].sort(key=lambda k: MOD_ORDER.index(k) if k in MOD_ORDER else 99)
            lst = sorted(merged.values(), key=lambda x: (-x["in_paper"], x["word"].lower()))
            per_set[setname] = lst
            with open(os.path.join(DATA, "hfw", setname + ".json"), "w", encoding="utf-8") as f:
                json.dump(lst, f, ensure_ascii=False, separators=(",", ":"))

    # 全局词库：附上词形还原索引
    forms = {}
    for k in words:
        for l in lemmas(k):
            if l not in forms:
                forms[l] = []
            forms[l].append(k)

    out = {
        "meta": {
            "total": len(words),
            "pages_scanned": n_pages,
            "source": "english-exam.lazynote.cn 六级真题高频词表",
            "note": "每个词含 CEFR 等级、词性释义、在真题中的出现频次",
        },
        "words": words,
        "forms": forms,
    }
    with open(os.path.join(DATA, "dict.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(os.path.join(DATA, "dict.json")) / 1024
    print(f"扫描页面: {n_pages}")
    print(f"全局词条: {len(words)}")
    print(f"词形索引: {len(forms)}")
    print(f"套次词表: {len(per_set)}")
    print(f"dict.json: {size:.0f} KB")
    print()
    top = sorted(words.items(), key=lambda x: -x[1]["freq"])[:12]
    print("最高频（按本卷累计次数）:")
    for w, d in top:
        print(f"  {w:<18} {d['cefr']:<3} {d['gloss'][:26]:<28} 累计 {d['freq']:>4} 次, 出现于 {len(d['papers'])} 套")


if __name__ == "__main__":
    main()
