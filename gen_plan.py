# -*- coding: utf-8 -*-
"""
生成备考打卡站（起始 2026-10-12 到考前 12-11，共 61 天；考试 12-12）。

输出到 site/plan/：
  index.html   打卡站单页（内联 CSS/JS，读精读站的 localStorage 做互通）
  plan.json    计划数据（供页面 fetch，也方便人工核对）

排程依据：建议.txt（刘晓艳两个月备考讲座逐字稿）
  阶段一 10/12-11/08  只做阅读 + 听力，写作翻译完全不碰（原文：「建议到11月8号」这一个月）
  阶段二 11/09-11/30  加写作 + 翻译，阅读听力继续但减量
  阶段三 12/01-12/11  整套模考 + 复盘
    （原文：「不进入12月份，我们没必要整套的做题」→ 阶段三从 12/01 起；
      模考日 12/01、12/04、12/07，12/10-11 考前只复盘）
  原文按两个月 60 天算（10/10 → 12/10），所以考试日定在 12/12 与讲座口径一致。
阅读顺序按讲座原文（建议.txt:34）：选词填空 -> 仔细阅读 -> 长篇阅读，由易到难。
"""
import datetime as dt
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_tpl import PAGE_TPL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "site", "plan")

START = dt.date(2026, 10, 12)         # 第一天 = 10/12（改这里要同步 plan_tpl 的静态文案 + 迁移链）
EXAM = dt.date(2026, 12, 12)          # 六级考试日（周六）
PHASE1_END = dt.date(2026, 11, 8)     # 建议.txt：「建议到11月8号」这一个月只动阅读+听力
PHASE2_END = dt.date(2026, 11, 30)    # 建议.txt：「不进入12月份，我们没必要整套的做题」

SETS = ["2023-06-1", "2023-06-2", "2023-06-3",
        "2023-12-1", "2023-12-2", "2023-12-3",
        "2024-06-1", "2024-06-2", "2024-06-3",
        "2024-12-1", "2024-12-2", "2024-12-3",
        "2025-06-1", "2025-06-2", "2025-06-3"]

MODULE_NAMES = {
    "writing": "写作", "listening": "听力", "cloze": "选词填空",
    "longreading": "长篇阅读", "reading1": "仔细阅读①",
    "reading2": "仔细阅读②", "translation": "翻译",
}
READING_MODS = ["cloze", "reading1", "reading2"]   # 阶段一：由易到难，跳过长篇阅读
PHASE2_MODS = ["longreading"]                       # 长篇阅读最难，留到阶段二

STEPS = ["按方法做题", "核实对错", "精读全文", "句子里背单词"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_meta():
    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        return json.load(f)


def build_schedule(meta):
    """排日程（10/12 起，到考前 12/11，共 61 天）。返回 (days, stats)"""
    papers = {p["set"]: p for p in meta["papers"]}

    # 阶段一池：选词填空 -> 仔细阅读① -> 仔细阅读②（由易到难），共 45 篇
    queue = []
    for mod in READING_MODS:
        for s in SETS:
            p = papers.get(s)
            if p and mod in p["modules"]:
                queue.append((s, mod))
    # 阶段二池：长篇阅读，共 15 篇
    queue2 = []
    for mod in PHASE2_MODS:
        for s in SETS:
            p = papers.get(s)
            if p and mod in p["modules"]:
                queue2.append((s, mod))

    # 可用的听力（第 3 套普遍缺听力）
    listen_sets = [s for s in SETS
                   if papers.get(s) and "listening" in papers[s]["modules"]]

    days = []
    d = START
    qi = 0
    q2i = 0
    day_no = 0
    p3_first = None          # 阶段三首日的 day_no：模考循环锚它，起始日挪动时模考日才不会漂
    while d < EXAM:          # 不含考试当天，共 61 天（10/12–12/11）
        day_no += 1
        if d <= PHASE1_END:
            phase = 1
        elif d <= PHASE2_END:
            phase = 2
        else:
            phase = 3

        item = {"d": d.isoformat(), "day": day_no, "phase": phase,
                "weekday": ["周一", "周二", "周三", "周四", "周五",
                            "周六", "周日"][d.weekday()],
                "reading": None, "listening": None,
                "extra": None, "review": False, "steps": []}

        if phase == 1:
            # 一天一篇阅读
            if qi < len(queue):
                s, mod = queue[qi]
                qi += 1
                item["reading"] = {"set": s, "mod": mod}
                item["steps"] = list(STEPS)
            # 听力：10 套整齐循环（第 3 套缺听力，已从 listen_sets 剔除）
            rnd = (day_no - 1) // len(listen_sets) + 1   # 第几轮：1,2,3
            item["listening"] = {
                "set": listen_sets[(day_no - 1) % len(listen_sets)],
                "mod": "listening",
                "round": rnd,
                # 模仿句数逐轮递增：第1轮 5 句，第2轮 10 句，第3轮 15 句
                "sentences": min(5 * rnd, 15),
            }
            # 每 3 天复盘一次
            if day_no > 1 and day_no % 3 == 1:
                item["review"] = True
                item["note"] = "复盘日：今天不做新阅读，把前 3 篇的单词和错题过一遍。"

        elif phase == 2:
            # 阅读转为隔天一篇（复盘为主），做长篇阅读
            if day_no % 2 == 1 and q2i < len(queue2):
                s, mod = queue2[q2i]
                q2i += 1
                item["reading"] = {"set": s, "mod": mod}
                item["steps"] = list(STEPS)
            item["listening"] = {
                "set": listen_sets[(day_no - 1) % len(listen_sets)],
                "mod": "listening",
                "round": 4 + (day_no - 1) // len(listen_sets),
                "sentences": 15,
            }
            # 写作 / 翻译轮着来
            if day_no % 2 == 0:
                item["extra"] = {"mod": "writing",
                                 "set": SETS[(day_no // 2) % len(SETS)]}
            else:
                item["extra"] = {"mod": "translation",
                                 "set": SETS[(day_no // 2) % len(SETS)]}
            if day_no % 3 == 0:
                item["review"] = True

        else:
            # 阶段三：整套模考 + 复盘。考前几天只复盘，不再模考。
            if p3_first is None:
                p3_first = day_no
            days_to_exam = (EXAM - d).days
            if days_to_exam <= 2:
                item["review"] = True
                item["note"] = ("考前 %d 天：只看错题本和生词本，不做新题，"
                                "调好作息。" % days_to_exam)
            else:
                idx = (day_no - p3_first) % 3
                if idx == 0:
                    # 模考日：整套做
                    s = SETS[-(1 + (day_no // 3) % 6)]
                    item["reading"] = {"set": s, "mod": None, "whole": True}
                    item["note"] = "整套模考：按考试时间一次做完，中途不停。"
                elif idx == 1:
                    item["note"] = "对答案 + 看错题本，逐个写清错因。"
                    item["review"] = True
                else:
                    item["note"] = "重读生词本里的词，回到原句里再读一遍。"
                    item["review"] = True

        days.append(item)
        d += dt.timedelta(days=1)

    total_reading = sum(1 for x in days if x["reading"] and not x["reading"].get("whole"))
    stats = {
        "total_days": len(days),
        "phase1": sum(1 for x in days if x["phase"] == 1),
        "phase2": sum(1 for x in days if x["phase"] == 2),
        "phase3": sum(1 for x in days if x["phase"] == 3),
        "reading_planned": total_reading,
        "reading_pool_p1": len(queue),
        "reading_pool_p2": len(queue2),
        "listen_sets": len(listen_sets),
    }
    return days, stats


def build_html(plan):
    """渲染打卡站单页。数据由 plan.json 内联注入，避免 fetch 的 file:// 限制。"""
    data = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
    # 资源版本号：跟精读站同一个写法，免得浏览器拿旧缓存
    ver = dt.datetime.now().strftime("%Y%m%d%H%M")
    return PAGE_TPL.replace("__DATA__", data).replace("__VER__", ver)


def main():
    meta = load_meta()
    days, stats = build_schedule(meta)
    os.makedirs(OUT, exist_ok=True)

    plan = {
        "generated": dt.date.today().isoformat(),
        "exam_date": EXAM.isoformat(),
        "start_date": START.isoformat(),
        "phase_bounds": {
            "1": [START.isoformat(), PHASE1_END.isoformat()],
            "2": [(PHASE1_END + dt.timedelta(days=1)).isoformat(), PHASE2_END.isoformat()],
            "3": [(PHASE2_END + dt.timedelta(days=1)).isoformat(),
                  (EXAM - dt.timedelta(days=1)).isoformat()],
        },
        "module_names": MODULE_NAMES,
        "steps": STEPS,
        "stats": stats,
        "days": days,
    }
    with open(os.path.join(OUT, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_html(plan))
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return plan


if __name__ == "__main__":
    main()