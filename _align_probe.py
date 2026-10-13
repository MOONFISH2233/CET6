# -*- coding: utf-8 -*-
"""查一下：停顿检测能不能当「句子起点」用。

思路：人声起始点 = 每段停顿的结束时间。如果长停顿（>=0.6s）的数量
接近该篇的真实句数，就能把「每句的时间」直接标定到停顿上，
比按字符占比插值准得多。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def pauses(mp3, noise="-32dB", dur=0.35):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", mp3, "-af",
         "silencedetect=noise=%s:d=%s" % (noise, dur), "-f", "null", "-"],
        capture_output=True, text=True, errors="replace").stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(st, en))


def main():
    setname = sys.argv[1] if len(sys.argv) > 1 else "2024-06-1"
    mp3 = os.path.join(HERE, "site", "audio", setname + ".mp3")
    aud = json.load(open(os.path.join(DATA, "audio", setname + ".json"), encoding="utf-8"))

    for noise in ("-32dB", "-35dB"):
        ps = pauses(mp3, noise)
        # 只看「长停顿」的结束点 = 下一句的起点
        for thr in (0.5, 0.6, 0.8):
            starts = [e for (s, e) in ps if e - s >= thr]
            print("%s ≥%.1fs → 人声起点 %d 个" % (noise, thr, len(starts)))
        print()

    print("=== 每篇：真实句数 vs 该篇区间内的长停顿数 ===")
    ps = pauses(mp3, "-32dB")
    starts = [e for (s, e) in ps if e - s >= 0.6]
    for pc in aud["pieces"]:
        n_lines = len(pc["lines"])
        inside = [t for t in starts if pc["start"] - 1 <= t <= pc["end"] + 1]
        print("  %-28s 句 %2d · 区间内长停顿 %2d   区间 %.1f–%.1f" %
              (pc["label"], n_lines, len(inside), pc["start"], pc["end"]))

    print("\n=== 抽样：第一篇前 8 句的插值时间 vs 最近的长停顿 ===")
    pc = aud["pieces"][0]
    for ln in pc["lines"][:8]:
        near = min(starts, key=lambda t: abs(t - ln["t0"])) if starts else None
        print("  句%-2s 插值 %7.1f  最近停顿 %7.1f  差 %5.1f   %s" %
              (ln["idx"], ln["t0"], near or -1, (near - ln["t0"]) if near else 0,
               ln["en"][:44]))


if __name__ == "__main__":
    main()
