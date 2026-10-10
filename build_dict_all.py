# -*- coding: utf-8 -*-
"""
用 ECDICT 做一份兜底词库，让文章里每个词都能点出释义。

背景：site/dict.json 来自懒笔记的「真题高频词」表（2062 词），那是按难度挑过的榜单、
不是词典 —— 实测真题文本有 12,742 个不同词形，能查到的只有 16.6%，缺的还净是
the / children / made 这类基础词和变形。这里把 ECDICT 裁成「语料出现过的词 + cet4/cet6 词」，
前端在 dict.json 查不到时懒加载它兜底。

数据源：https://github.com/skywind3000/ECDICT   (MIT License, Copyright (c) Linwei)
缓存：_cache/ecdict.csv（62.9MB，不进 git；缺失时用 MIRRORS 里的地址下载）
输出：data/dict_all.json → 拷到 site/dict_all.json
  {"lemmas": {"word": "中文释义"}, "forms": {"词形": "原形"}, "tags": {"word": "cet4 cet6"}, "meta": {}}
"""
import collections
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SITE = os.path.join(HERE, "site")
CACHE = os.path.join(HERE, "_cache", "ecdict.csv")

MIRRORS = [
    "https://ghfast.top/https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv",
    "https://ghproxy.net/https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv",
]

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
KEEP_TAGS = ("zk", "gk", "cet4", "cet6", "ky", "toefl", "ielts", "gre")
FORM_CODES = ("p", "d", "i", "3", "r", "t", "s")   # 过去式/过去分词/现在分词/三单/比较级/最高级/复数

# 手工覆盖表：ECDICT 收得不好（罐头 can、art. 那 the）或干脆没有的高频词。
# 在 ECDICT 之后应用，**覆盖**它的释义。
ABBREV = {
    # 功能词：ECDICT 要么太敷衍要么给的是错义项
    "the": "art. 定冠词：这个/那个（特指已提到或双方已知的人或物）",
    "a": "art. 一个（不定冠词，用于辅音音素前）；每一",
    "an": "art. 一个（不定冠词，用于元音音素前）",
    "be": "v. 是，在，成为（am/is/are/was/were/been 的原形）",
    "can": "aux. 能，会，可以；n. 罐头；vt. 装罐",
    "could": "aux. can 的过去式；能，可以（语气更委婉）",
    "may": "aux. 可以，可能；n. 五月",
    "must": "aux. 必须，一定；n. 必须做的事",
    "that": "pron./a. 那，那个；conj. 引导从句（that 从句）",
    "this": "pron./a. 这，这个",
    "it": "pron. 它；这（指代前文事物、天气、时间等）",
    "of": "prep. …的；属于；由…组成",
    "to": "prep. 到，向，对于；（不定式符号）",
    "and": "conj. 和，与，而且",
    # 缩写（真题里反复出现，ECDICT 没有或只收别的义项）

    "ai": "abbr. 人工智能（Artificial Intelligence）",
    "gdp": "abbr. 国内生产总值（Gross Domestic Product）",
    "eu": "abbr. 欧盟（European Union）",
    "cctv": "abbr. 中国中央电视台",
    "aap": "abbr. 美国儿科学会（American Academy of Pediatrics）",
    "un": "abbr. 联合国（United Nations）",
    "uk": "abbr. 英国（United Kingdom）",
    "us": "pron. 我们（we 的宾格）；abbr. 美国",
    "usa": "abbr. 美国（United States of America）",
    "ceo": "abbr. 首席执行官（Chief Executive Officer）",
    "phd": "abbr. 博士学位",
    "tv": "abbr. 电视（television）",
    "sb": "abbr. 某人（词典缩略语 somebody）",
    "sth": "abbr. 某物（词典缩略语 something）",
    "th": "后缀：构成序数词，如 4th 第四",
    "st": "abbr. 圣（Saint）；街（street）",
    "id": "n. 身份证（ID）；本我（心理学术语）",
    "hr": "abbr. 人力资源（Human Resources）；小时（hour）",
}


def corpus_tokens():
    """所有试卷 JSON 里的英文词形 -> 出现次数。"""
    cnt = collections.Counter()
    pdir = os.path.join(DATA, "paper")
    for fn in os.listdir(pdir):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(pdir, fn), encoding="utf-8") as f:
            data = json.load(f)

        def walk(x):
            if isinstance(x, str):
                for m in WORD_RE.findall(x):
                    w = m.lower()
                    if len(w) == 1 and w not in ("a", "i"):
                        continue      # b/c/d 这类选项字母不算
                    cnt[w] += 1
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)

        walk(data)
    return cnt


def clean_gloss(t):
    """ECDICT 的 translation：义项用字面 \\n 分隔。

    [医]/[经]/[计]/[化] 是领域标记：优先取没有标记的行（通用义），
    一行都没有时才退回去掉标记的领域义 —— 否则 competitiveness / hierarchical 这种
    整行带标记的词会变成查不到，而 his 这种又会混进「组氨酸」这种噪声。
    """
    if not t:
        return ""
    clean, tagged = [], []
    for ln in t.replace("\\n", "\n").split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("[网络]"):
            continue
        m = re.match(r"^\[[^\]]{1,6}\]\s*(.*)$", ln)
        if m:
            if m.group(1).strip():
                tagged.append(m.group(1).strip())
        else:
            clean.append(ln)
    parts = (clean or tagged)[:2]
    g = re.sub(r"\s+", " ", "；".join(parts)).strip("；; ")
    return g[:80]


def contraction_base(tok):
    """don't -> do、company's -> company（够用的规则版）。"""
    if "'" not in tok:
        return None
    base = tok.split("'")[0]
    if tok.endswith("n't") and base.endswith("n"):
        base = base[:-1]
    return base or None


def main():
    if not os.path.exists(CACHE):
        print("缺少 " + CACHE)
        print("先下载 ECDICT（任一地址）：")
        for u in MIRRORS:
            print("  " + u)
        sys.exit(1)

    corpus = corpus_tokens()
    print("语料词形: %d（含重复共 %d 次）" % (len(corpus), sum(corpus.values())))

    lemmas, tags, raw_forms = {}, {}, {}
    with open(CACHE, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            w = (row.get("word") or "").strip().lower()
            if not w or " " in w:            # 词组不收，只收单词
                continue
            tag = (row.get("tag") or "").strip()
            if w not in corpus and "cet4" not in tag and "cet6" not in tag:
                continue
            g = clean_gloss(row.get("translation") or "")
            if not g:
                continue
            lemmas[w] = g
            keep = [t for t in tag.split() if t in KEEP_TAGS]
            if keep:
                tags[w] = " ".join(keep)
            raw_forms[w] = row.get("exchange") or ""

    # 词形 -> 原形（别把真词条盖掉）
    forms = {}
    for w, ex in raw_forms.items():
        for part in ex.split("/"):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            v = v.strip().lower()
            if k in FORM_CODES and v and v != w and v not in lemmas:
                forms[v] = w
    # 缩写/所有格
    for tok in corpus:
        if tok in lemmas or tok in forms:
            continue
        b = contraction_base(tok)
        if b and (b in lemmas or b in forms):
            forms[tok] = b

    # 手工覆盖表：无条件生效（可以盖掉 ECDICT 的错误/敷衍义项）
    for w, g in ABBREV.items():
        if w in corpus or w in lemmas:
            lemmas[w] = g
            tags.pop(w, None)      # 手写释义的词不再挂考级标签（the 挂「高考」很怪）

    # 连字符复合词：year-old / work-related —— 拆开各取释义拼一句
    def gloss_of(t):
        if t in lemmas:
            return lemmas[t]
        f = forms.get(t)
        if f and f in lemmas:
            return lemmas[f]
        return ""

    for tok in corpus:
        if tok in lemmas or tok in forms or "-" not in tok:
            continue
        parts = [p for p in tok.split("-") if p]
        gs = [(p, gloss_of(p)) for p in parts]
        if len(gs) >= 2 and all(g for _, g in gs):
            lemmas[tok] = "复合词： " + " + ".join("%s（%s）" % (p, g[:18]) for p, g in gs)

    out = {
        "meta": {
            "source": "ECDICT (MIT License, Copyright (c) Linwei) "
                      "https://github.com/skywind3000/ECDICT",
            "note": "dict.json 查不到时的兜底词库；只收本站语料词 + cet4/cet6 词",
            "lemmas": len(lemmas),
            "forms": len(forms),
        },
        "lemmas": lemmas,
        "forms": forms,
        "tags": tags,
    }
    dst = os.path.join(DATA, "dict_all.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "dict_all.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    # 覆盖率：dict.json（含词形表） + dict_all 一起算
    core = json.load(open(os.path.join(DATA, "dict.json"), encoding="utf-8"))
    cw, cf = core["words"], core.get("forms", {})

    def resolvable(t):
        if t in cw or t in cf or t in lemmas:
            return True
        f = forms.get(t)
        if not f:
            return False
        return f in lemmas or f in cw or f in cf or forms.get(f) in lemmas

    miss = [t for t in corpus if not resolvable(t)]
    size = os.path.getsize(dst) / 1024
    print("词条 %d · 词形 %d · dict_all.json %.0f KB" % (len(lemmas), len(forms), size))
    print("覆盖率: %.2f%% → %.2f%%（未覆盖 %d 个词形）" % (
        100.0 * sum(v for t, v in corpus.items() if t in cw or t in cf) / sum(corpus.values()),
        100.0 * sum(v for t, v in corpus.items() if resolvable(t)) / sum(corpus.values()),
        len(miss)))
    top = sorted(miss, key=lambda t: -corpus[t])[:40]
    if top:
        print("未覆盖最高频 40 个:")
        for t in top:
            print("   %-16s %d 次" % (t, corpus[t]))


if __name__ == "__main__":
    main()
