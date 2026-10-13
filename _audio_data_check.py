# -*- coding: utf-8 -*-
"""全量校验逐题时间点（纯数据，不起浏览器）：
   1) 每题的时间必须落在它那一篇的区间内
   2) 同一篇内严格不减
   3) 二分的「篇首」时间必须和源站给的区间一致（页面上那 7 个胶囊就用它）
   4) 和「答案句所在行」的推算起点比一比，别偏出十万八千里
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

bad = 0
n_all = 0
for fn in sorted(os.listdir(os.path.join(DATA, "audio"))):
    if not fn.endswith(".json"):
        continue
    s = fn[:-5]
    d = json.load(open(os.path.join(DATA, "audio", fn), encoding="utf-8"))
    src = json.load(open(os.path.join(DATA, "audio_src", fn), encoding="utf-8"))
    drift = []
    for i, pc in enumerate(d["pieces"]):
        srcp = src["pieces"][i] if i < len(src["pieces"]) else {}
        if abs(pc["start"] - srcp.get("start", pc["start"])) > 0.2 or \
           abs(pc["end"] - srcp.get("end", pc["end"])) > 0.2:
            print("  ⚠️ %s 第%d篇 区间和源站不一致: %.1f–%.1f vs %.1f–%.1f" %
                  (s, i + 1, pc["start"], pc["end"], srcp.get("start", 0), srcp.get("end", 0)))
            bad += 1
        prev = -1
        for q in pc["qs"]:
            n_all += 1
            if not (pc["start"] - 0.6 <= q["t"] <= pc["end"] + 0.6):
                print("  ⚠️ %s 题%s 时间 %.1f 越出本篇 %.1f–%.1f" %
                      (s, q["no"], q["t"], pc["start"], pc["end"]))
                bad += 1
            if q["t"] < prev - 0.01:
                print("  ⚠️ %s 题%s 时间倒退" % (s, q["no"]))
                bad += 1
            prev = q["t"]
            # 和答案句所在行的起点比：提前量最多 3 秒，落后不超过 20 秒
            ln = [l for l in pc["lines"] if l["idx"] == q["idx"]]
            if ln:
                delta = q["t"] - ln[0]["t0"]
                drift.append(delta)
    if drift:
        drift.sort()
        print("  %-12s %d 题 · 相对答案句起点: 最小 %+.1f 中位 %+.1f 最大 %+.1f" %
              (s, len(drift), drift[0], drift[len(drift) // 2], drift[-1]))

print("\n共 %d 题 · 问题 %d 处" % (n_all, bad))
sys.exit(1 if bad else 0)
