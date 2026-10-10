# -*- coding: utf-8 -*-
"""
从懒笔记 (english-exam.lazynote.cn) 抓取六级真题【解析】页面。

路径规则（已实测确认）：
  解析页在 /cet6/sections/ 下，注意不是 /cet6/paper/（那个是纯卷面无解析）
    /cet6/sections/<set>/part1/                 写作
    /cet6/sections/listening/<set>/             听力（注意 listening 在前，set 在后）
    /cet6/sections/<set>/part3-section-a/       选词填空
    /cet6/sections/<set>/part3-section-b/       长篇阅读
    /cet6/sections/<set>/part3-section-c-1/     仔细阅读 1
    /cet6/sections/<set>/part3-section-c-2/     仔细阅读 2
    /cet6/sections/<set>/part-iv/               翻译

抓下来的原始 HTML 存到 raw/<set>/<name>.html，已存在就跳过（断点续传）。
"""
import os
import sys
import time
import urllib.request
import urllib.error

BASE = "https://english-exam.lazynote.cn"

# 要抓的考期：2022-06 起到 2026-06
# 含疫情延期场次：2022-09、2023-03
SETS = []
for year, months in [
    (2022, ["06", "09", "12"]),
    (2023, ["03", "06", "12"]),
    (2024, ["06", "12"]),
    (2025, ["06", "12"]),
    (2026, ["06"]),
]:
    for m in months:
        for s in ("1", "2", "3"):
            SETS.append(f"{year}-{m}-{s}")

# 每套要抓的页面：(本地文件名, [候选 URL 路径模板, ...])
# 源站 2025-06 起把「仔细阅读」两篇合并成 part3-section-c，
# 所以 c-1 的位置要给两个候选路径，先试新的、再试旧的。
PAGES = [
    ("part1",            ["sections/{set}/part1/"]),
    ("listening",        ["sections/listening/{set}/"]),
    ("part3-section-a",  ["sections/{set}/part3-section-a/"]),
    ("part3-section-b",  ["sections/{set}/part3-section-b/"]),
    ("part3-section-c-1", ["sections/{set}/part3-section-c/",
                           "sections/{set}/part3-section-c-1/"]),
    ("part3-section-c-2", ["sections/{set}/part3-section-c-2/"]),
    ("part-iv",          ["sections/{set}/part-iv/"]),
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")


def fetch(url, retries=3):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    sets = [s for s in SETS if (not only or s in only)]
    total = len(sets) * len(PAGES)
    done = skipped = failed = 0
    errors = []

    print(f"计划抓取 {len(sets)} 套 x {len(PAGES)} 页 = {total} 个页面\n", flush=True)

    for si, s in enumerate(sets, 1):
        outdir = os.path.join(RAW, s)
        os.makedirs(outdir, exist_ok=True)
        line = []
        for name, tmpls in PAGES:
            dst = os.path.join(outdir, name + ".html")
            if os.path.exists(dst) and os.path.getsize(dst) > 20000:
                skipped += 1
                continue
            body = None
            last_err = None
            for tmpl in tmpls:
                url = BASE + "/cet6/" + tmpl.format(set=s)
                try:
                    body = fetch(url)
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(0.3)
            if body is not None:
                with open(dst, "wb") as f:
                    f.write(body)
                done += 1
                line.append(f"{name}:{len(body)//1000}k")
            else:
                failed += 1
                code = getattr(last_err, "code", "")
                errors.append((s, name, f"HTTP {code}" if code else str(last_err)[:50]))
                line.append(f"{name}:ERR{code}")
            time.sleep(0.4)  # 限速
        print(f"[{si:>2}/{len(sets)}] {s:<12} " + "  ".join(line), flush=True)

    print(f"\n{'='*70}")
    print(f"新下载 {done}  已存在 {skipped}  失败 {failed}  共 {total}")
    if errors:
        print("\n失败清单：")
        for s, n, e in errors:
            print(f"  {s} / {n}: {e}")


if __name__ == "__main__":
    main()
