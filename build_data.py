# -*- coding: utf-8 -*-
"""
把 raw/ 下抓到的 HTML 全部解析成结构化 JSON，输出到 data/。

输出结构：
  data/index.json          总索引（考期、套次、各模块可用性）
  data/paper/<set>.json    每套卷的完整数据

每个 <set>.json 结构：
{
  "set": "2022-06-1",
  "year": 2022, "month": 6, "no": 1,
  "label": "2022年6月 · 第1套",
  "modules": {
     "writing":      {...},    # Part I
     "listening":    {...},    # Part II
     "cloze":        {...},    # Part III A 选词填空
     "longreading":  {...},    # Part III B 长篇阅读
     "reading1":     {...},    # Part III C(1)
     "reading2":     {...},    # Part III C(2)
     "translation":  {...}     # Part IV
  },
  "missing": ["listening", ...]   # 该套缺哪些模块（源站没有）
}
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parse_reading as R          # noqa: E402
import parse_trans as T            # noqa: E402
import parse_listening as L        # noqa: E402
import parse_others as O           # noqa: E402

RAW = os.path.join(HERE, "raw")
DATA = os.path.join(HERE, "data")

# 本地文件名 -> (模块 key, 解析函数)
MODULES = [
    ("writing",     "part1",            lambda h: O.parse_writing(h)),
    ("listening",   "listening",        lambda h: L.parse_listening(h)),
    ("cloze",       "part3-section-a",  lambda h: O.parse_banked_cloze(h)),
    ("longreading", "part3-section-b",  lambda h: O.parse_long_reading(h)),
    ("reading1",    "part3-section-c-1", lambda h: R.parse_html(h)),
    ("reading2",    "part3-section-c-2", lambda h: R.parse_html(h)),
    ("translation", "part-iv",          lambda h: T.parse_translation(strip(h))),
]


def strip(h):
    from parse_lib import strip_scripts
    return strip_scripts(h)


def load_html(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_set(setname):
    d = os.path.join(RAW, setname)
    if not os.path.isdir(d):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d)", setname)
    if not m:
        return None
    year, month, no = int(m.group(1)), int(m.group(2)), int(m.group(3))

    out = {
        "set": setname,
        "year": year,
        "month": month,
        "no": no,
        "label": f"{year}年{month}月 · 第{no}套",
        "modules": {},
        "missing": [],
    }

    for key, fname, fn in MODULES:
        p = os.path.join(d, fname + ".html")
        if not os.path.exists(p) or os.path.getsize(p) < 20000:
            out["missing"].append(key)
            continue
        try:
            out["modules"][key] = fn(load_html(p))
        except Exception as e:  # noqa: BLE001
            out["missing"].append(key)
            out.setdefault("errors", {})[key] = f"{type(e).__name__}: {e}"
    return out


def main():
    sets = sorted([x for x in os.listdir(RAW) if os.path.isdir(os.path.join(RAW, x))])
    print(f"发现 {len(sets)} 个套次目录\n")

    os.makedirs(DATA, exist_ok=True)
    papers_dir = os.path.join(DATA, "paper")
    os.makedirs(papers_dir, exist_ok=True)

    index = []
    total_mods = 0

    for s in sets:
        data = parse_set(s)
        if not data:
            print(f"  跳过 {s}")
            continue
        with open(os.path.join(papers_dir, s + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

        mods = list(data["modules"].keys())
        total_mods += len(mods)
        miss = data["missing"]
        flag = "" if not miss else "  缺: " + ",".join(miss)
        err = data.get("errors")
        if err:
            flag += "  ERR: " + ",".join(err.keys())
        print(f"  {data['label']:<18} {len(mods)} 模块{flag}")

        index.append({
            "set": s, "label": data["label"],
            "year": data["year"], "month": data["month"], "no": data["no"],
            "modules": mods, "missing": miss,
        })

    # 按考期分组，便于站点按考期导航
    periods = {}
    for it in index:
        pk = f"{it['year']}-{it['month']:02d}"
        periods.setdefault(pk, []).append(it["set"])

    meta = {
        "generated": "2026-10-10",
        "source": "english-exam.lazynote.cn",
        "total_sets": len(index),
        "total_modules": total_mods,
        "periods": [{"period": k, "sets": sorted(v)} for k, v in sorted(periods.items(), reverse=True)],
        "papers": index,
        "module_names": {
            "writing": "写作", "listening": "听力", "cloze": "选词填空",
            "longreading": "长篇阅读", "reading1": "仔细阅读(1)",
            "reading2": "仔细阅读(2)", "translation": "翻译",
        },
    }
    with open(os.path.join(DATA, "index.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n{'='*60}")
    print(f"套次 {len(index)}   模块总数 {total_mods}   考期 {len(periods)}")
    print(f"输出: {DATA}")


if __name__ == "__main__":
    main()
