# -*- coding: utf-8 -*-
"""
把「每篇的音频区间」和「我们自己的逐句文本」对上，算出**每道题的播放位置**。

源站只给到篇（Section A 第 1 篇 = 35.9–208.6s），没有逐题时间点。
做法：
  1. 每题解析里都有一条「定位」（答案句）—— 拿它去本篇的逐句文本里找它对应第几句
  2. 每篇内部按**字符数占比**把区间分给各句（同一个人连续读，语速均匀，误差通常几秒内）
  3. 导出每题的时间点，写进 data/audio/<set>.json（gen_site 用它渲染「听这题」）

产物：data/audio/<set>.json
  { set, mp3, total, pieces:[{label,start,end,lines:[{idx,en,zh,t0,t1}],qs:[{no,t}]}] }
用法：python build_audio_map.py [set ...]        默认全部有音频的套
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PAPER = os.path.join(DATA, "paper")
SRC_META = os.path.join(DATA, "audio_src")
OUT = os.path.join(DATA, "audio")


def norm(s):
    """只留小写字母和空格，方便跟源站句子比对"""
    return re.sub(r"[^a-z ]+", " ", str(s or "").lower()).strip()


def loose(s):
    """更松：去掉所有非字母"""
    return re.sub(r"[^a-z]+", "", str(s or "").lower())


def qrange(label):
    """'Section A · 第 1 篇 · 1–4 题' → (1, 4)"""
    m = re.search(r"(\d+)\s*[–\-—]\s*(\d+)", label)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)", label)
    return (int(m.group(1)), int(m.group(1))) if m else (0, 0)


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build(setname):
    meta_p = os.path.join(SRC_META, setname + ".json")
    paper_p = os.path.join(PAPER, setname + ".json")
    if not (os.path.exists(meta_p) and os.path.exists(paper_p)):
        print("  %-12s 缺数据，跳过" % setname)
        return None
    meta = load_json(meta_p)
    paper = load_json(paper_p)
    aud = paper["modules"].get("listening")
    if not aud:
        print("  %-12s 没有听力模块" % setname)
        return None

    trs = aud.get("transcripts", [])
    qs = aud.get("questions", [])
    pieces = meta.get("pieces", [])
    if len(trs) != len(pieces):
        print("  %-12s ⚠️ 篇数不齐：我们 %d 篇 / 源站 %d 篇" % (setname, len(trs), len(pieces)))

    out_pieces, matched, missed = [], 0, []
    for i, tr in enumerate(trs):
        pc = pieces[i] if i < len(pieces) else {"label": tr.get("head", ""), "start": tr.get("seek", 0), "end": 0}
        start = float(pc.get("start") or tr.get("seek") or 0)
        end = float(pc.get("end") or 0) or start + 120      # 兜底：没 end 就给 2 分钟
        lines = tr.get("lines", [])
        # 按字符数占比分配区间（对话里每句一个说话人，语速近似均匀）
        wsum = sum(max(1, len(loose(l.get("en")))) for l in lines) or 1
        acc = start
        out_lines = []
        for l in lines:
            w = max(1, len(loose(l.get("en"))))
            t0 = acc
            acc += (end - start) * w / wsum
            out_lines.append({"idx": l.get("idx"), "en": l.get("en", ""), "zh": l.get("zh", ""),
                              "t0": round(t0, 1), "t1": round(acc, 1)})

        # 这一篇覆盖哪些题
        qa, qb = qrange(pc.get("label", ""))
        this_qs = []
        for q in qs:
            no = q.get("no")
            if not (qa <= no <= qb):
                continue
            ans_en = ((q.get("locate") or {}).get("en") or "").strip()
            if not ans_en:
                # 退一步：从解析的「定位」字段里取英文部分
                loc = (q.get("analysis") or {}).get("定位", "")
                m = re.search(r"([A-Za-z][^。]{6,})", loc)
                ans_en = m.group(1) if m else ""
            target = loose(ans_en)
            hit = None
            if target:
                # 精确：某一句就是它
                for ln in out_lines:
                    if loose(ln["en"]) and loose(ln["en"]) == target:
                        hit = ln
                        break
                # 近似：答案句是该句的一部分 / 反过来（取重叠最多的一句）
                if hit is None:
                    best, best_n = None, 0
                    for ln in out_lines:
                        a, b = loose(ln["en"]), target
                        if not a:
                            continue
                        n = 0
                        for L in range(min(len(a), len(b)), 5, -2):
                            for s in range(0, len(a) - L + 1):
                                if b.find(a[s:s + L]) >= 0:
                                    n = L
                                    break
                            if n:
                                break
                        if n > best_n:
                            best, best_n = ln, n
                    # 至少要有一小半重合才认，免得乱指
                    if best is not None and best_n >= max(12, len(target) * 0.35):
                        hit = best
            if hit:
                matched += 1
                # ⚠️ 我们这边的「一句」有时是源站的好几句拼起来的（题 13/14 会落到同一行）。
                # 答案句只占其中一部分时，按字符占比在行内再切一刀，别让两题指同一个点。
                t = hit["t0"]
                if target and len(target) < len(loose(hit["en"])) * 0.8:
                    head = loose(hit["en"])
                    pos = head.find(target[:24])          # 答案句在行内的位置
                    if pos > 0:
                        frac = pos / max(1, len(head))
                        t = round(hit["t0"] + (hit["t1"] - hit["t0"]) * frac, 1)
                this_qs.append({"no": no, "t": t, "idx": hit["idx"]})
            else:
                missed.append(no)
                this_qs.append({"no": no, "t": round(start, 1), "idx": None})
        out_pieces.append({"label": pc.get("label", ""), "start": round(start, 1), "end": round(end, 1),
                           "lines": out_lines, "qs": this_qs})

    mp3 = "audio/%s.mp3" % setname
    total = max([p["end"] for p in out_pieces] or [0])
    res = {"set": setname, "mp3": mp3, "total": round(total, 1),
           "audio_id": meta.get("audio_id"), "pieces": out_pieces}
    return res, matched, len(qs), missed


def main():
    args = [a for a in sys.argv[1:]]
    sets = args or sorted(f[:-5] for f in os.listdir(SRC_META) if f.endswith(".json"))
    os.makedirs(OUT, exist_ok=True)
    tot_m = tot_q = 0
    for s in sets:
        r = build(s)
        if not r:
            continue
        res, matched, nq, missed = r
        p = os.path.join(OUT, s + ".json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
        tot_m += matched
        tot_q += nq
        flag = "✓" if matched == nq else "⚠️"
        print("  %-12s %s 逐题定位 %d/%d%s" % (s, flag, matched, nq,
              ("  没对上: " + ",".join(map(str, missed))) if missed else ""))
    print("\n合计 %d/%d 题对上（%.0f%%）" % (tot_m, tot_q, 100.0 * tot_m / max(1, tot_q)))


if __name__ == "__main__":
    main()
