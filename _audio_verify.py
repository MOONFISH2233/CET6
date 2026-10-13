# -*- coding: utf-8 -*-
"""校验逐题时间点：吸附后是不是真的落在「语音起点」上、顺序对不对、有没有越界。

「语音起点」= 静音段结束的那一刻。落在这上面，说明是从一句话的开头开始放，
不会出现「点进去已经在读半句」。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def starts_of(mp3):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp3, "-af",
                          "silencedetect=noise=-32dB:d=0.35", "-f", "null", "-"],
                         capture_output=True, text=True, errors="replace").stderr
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return en


def main():
    sets = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(os.path.join(DATA, "audio")))
    bad = 0
    tot_q = tot_on = 0
    for s in sets:
        p = os.path.join(DATA, "audio", s + ".json")
        mp3 = os.path.join(HERE, "site", "audio", s + ".mp3")
        if not (os.path.exists(p) and os.path.exists(mp3)):
            continue
        d = json.load(open(p, encoding="utf-8"))
        st = starts_of(mp3)
        on_pause, near, n, offs = 0, 0, 0, []
        for pc in d["pieces"]:
            prev = -1
            for q in pc["qs"]:
                n += 1
                t = q["t"]
                if t < pc["start"] - 0.6 or t > pc["end"] + 0.6:
                    print("   ⚠️ %s 题 %s 越界: %.1f 不在 %.1f–%.1f" % (s, q["no"], t, pc["start"], pc["end"]))
                    bad += 1
                if t < prev:
                    print("   ⚠️ %s 题 %s 顺序倒了" % (s, q["no"]))
                    bad += 1
                prev = t
                # 和最近的语音起点的距离。⚠️ 要扣掉故意留的提前量（Q_LEAD），
                #    否则量出来的永远是 1.2 秒左右，看不出真实偏差
                dd = min((abs(x - (t + 1.2)) for x in st), default=999)
                offs.append(dd)
                if dd <= 0.3:
                    on_pause += 1
                if dd <= 3:
                    near += 1
        tot_q += n
        tot_on += on_pause
        offs.sort()
        med = offs[len(offs) // 2] if offs else -1
        print("  %-12s %2d 题 · 落在语音起点(≤0.3s) %2d · ≤3s %2d · 中位偏差 %.2fs" %
              (s, n, on_pause, near, med))
    print("\n合计 %d 题：正好落在语音起点 %d 题（%.0f%%）· 问题 %d 处" %
          (tot_q, tot_on, 100.0 * tot_on / max(1, tot_q), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
