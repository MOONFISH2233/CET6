# -*- coding: utf-8 -*-
"""
一键流水线：抓取 -> 解析成 JSON -> 生成静态站。

用法：
  python pipeline.py            全流程
  python pipeline.py --no-fetch 跳过抓取（只重解析+重生成）
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(script, label):
    print(f"\n{'='*64}")
    print(f"  {label}")
    print(f"{'='*64}")
    t0 = time.time()
    p = subprocess.run([PY, os.path.join(HERE, script)], cwd=HERE)
    dt = time.time() - t0
    if p.returncode != 0:
        print(f"\n!! {label} 失败 (exit {p.returncode})")
        sys.exit(p.returncode)
    print(f"  ({dt:.1f}s)")


def main():
    do_fetch = "--no-fetch" not in sys.argv
    if do_fetch:
        run("fetch.py", "1/3  抓取懒笔记解析页")
    else:
        print("跳过抓取（--no-fetch）")
    run("build_data.py", "2/3  解析 HTML 为结构化 JSON")
    run("build_dict.py", "3/6  构建词库（核心高频词）")
    run("build_dict_all.py", "4/6  构建兜底词库（ECDICT）")
    run("gen_site.py", "5/6  生成静态站点")
    run("gen_pdf.py", "6/6  生成 PDF（精读版 + 速查版）")
    print(f"\n{'='*64}")
    print("  完成。站点在: " + os.path.join(HERE, "site"))
    print(f"{'='*64}")


if __name__ == "__main__":
    main()
