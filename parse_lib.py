# -*- coding: utf-8 -*-
"""
懒笔记页面解析工具库。

不依赖第三方库（本机 Python 3.8，无 bs4/lxml 保证），用正则 + 手写标签扫描。
页面是 Astro 生成的服务端渲染 HTML，结构规整、class 命名稳定，正则够用。
"""
import html as _html
import re


# ---------------------------------------------------------------- 基础清洗

BLOCK_TAGS = {
    "p", "div", "li", "ul", "ol", "section", "article", "h1", "h2", "h3",
    "h4", "h5", "h6", "tr", "td", "th", "table", "br", "hr", "blockquote",
    "details", "summary", "figure", "figcaption",
}


def strip_scripts(h):
    h = re.sub(r"(?s)<script.*?</script>", "", h)
    h = re.sub(r"(?s)<style.*?</style>", "", h)
    h = re.sub(r"(?s)<!--.*?-->", "", h)
    return h


def unescape(s):
    s = _html.unescape(s)
    s = s.replace(" ", " ")
    return s


def to_text(frag):
    """把 HTML 片段转成纯文本（块级标签换行）。"""
    s = re.sub(r"(?s)<script.*?</script>", "", frag)
    s = re.sub(r"(?s)<style.*?</style>", "", frag)
    # 块级标签变换行
    s = re.sub(r"<(" + "|".join(BLOCK_TAGS) + r")\b[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"</(" + "|".join(BLOCK_TAGS) + r")>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = unescape(s)
    s = re.sub(r"[ \t　]+", " ", s)
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def one_line(frag):
    """把片段压成一行。"""
    return re.sub(r"\s+", " ", to_text(frag)).strip()


def inner_text_of(h, cls):
    """取第一个 class=cls 的元素的内文（一行）。"""
    m = re.search(r'<([a-z0-9]+)[^>]*class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"[^>]*>(.*?)</\1>',
                  h, re.S | re.I)
    return one_line(m.group(2)) if m else ""


def parse_hfw(h):
    """抽页面末尾的「真题高频词」表。

    结构：<li class="hfw__item">
            <a class="hfw__word" href="/cet6/words/<词>/">
              <span class="hfw__en">antibiotic</span>
              <span class="hfw__cefr">B2</span></a>
            <span class="hfw__gloss">n. 抗生素</span>
            <div class="hfw__bottom">
              <span class="hfw__stat">本卷16 次 · 真题 27 句</span>
    返回 [{"word", "cefr", "gloss", "in_paper", "in_exam"}, ...]
    """
    out = []
    seen = set()
    for m in re.finditer(r'<li[^>]*class="[^"]*\bhfw__item\b[^"]*"[^>]*>', h):
        sp = elem_span(h, m.start())
        if not sp:
            break
        item = h[m.start():sp[2]]
        w = re.search(r'hfw__en[^>]*>(.*?)</span>', item, re.S)
        if not w:
            continue
        word = one_line(w.group(1))
        if not word or word.lower() in seen:
            continue
        seen.add(word.lower())
        c = re.search(r'hfw__cefr[^>]*>(.*?)</span>', item, re.S)
        g = re.search(r'hfw__gloss[^>]*>(.*?)</span>', item, re.S)
        stat = re.search(r'hfw__stat[^>]*>(.*?)</span>\s*(?:<a|</div>)', item, re.S)
        in_paper = in_exam = 0
        if stat:
            nums = re.findall(r'num[^>]*>\s*(\d+)', stat.group(1))
            if len(nums) >= 1:
                in_paper = int(nums[0])
            if len(nums) >= 2:
                in_exam = int(nums[1])
        out.append({
            "word": word,
            "cefr": one_line(c.group(1)) if c else "",
            "gloss": one_line(g.group(1)) if g else "",
            "in_paper": in_paper,
            "in_exam": in_exam,
        })
    return out


def is_mostly_chinese(t):
    """（保留：其他地方可能用到）判断是否以中文为主。"""
    """判断一行文本是否以中文为主（中文字符占比 > 20%）。"""
    if not t:
        return False
    cjk = len(re.findall(r"[一-鿿]", t))
    letters = len(re.findall(r"[A-Za-z]", t))
    if cjk == 0:
        return False
    # 有中文，且中文比英文多，或中文占非空白字符的两成以上
    return cjk >= letters or cjk / max(1, len(t)) > 0.2


def elem_span(h, start):
    """从 start（'<' 的位置）出发，返回配对标签的结束位置（不含）。
    支持嵌套同名标签。返回 (inner_start, inner_end, elem_end)。"""
    m = re.match(r'<([a-zA-Z0-9]+)\b[^>]*?(/?)>', h[start:])
    if not m:
        return None
    tag = m.group(1).lower()
    selfclose = m.group(2) == "/"
    inner_start = start + m.end()
    if selfclose or tag in ("br", "img", "input", "hr", "meta", "link"):
        return inner_start, inner_start, inner_start
    depth = 1
    pos = inner_start
    pat = re.compile(r"<(/)?" + re.escape(tag) + r"\b[^>]*?>", re.I)
    while depth > 0:
        mm = pat.search(h, pos)
        if not mm:
            return inner_start, len(h), len(h)
        if mm.group(1):
            depth -= 1
        else:
            # 自闭合不算一层
            if not mm.group(0).rstrip().endswith("/>") and not re.match(r"<" + re.escape(tag) + r"\b[^>]*/>", mm.group(0), re.I):
                depth += 1
        pos = mm.end()
        if depth == 0:
            return inner_start, mm.start(), mm.end()
    return inner_start, len(h), len(h)


def find_blocks(h, cls):
    """找出所有含 class=cls 的元素的 (start, inner_start, inner_end, elem_end)。"""
    out = []
    for m in re.finditer(r'<([a-zA-Z0-9]+)\b[^>]*class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"[^>]*>', h):
        sp = elem_span(h, m.start())
        if sp:
            out.append((m.start(),) + sp)
    return out


def find_by_attr(h, attr, value):
    """找 attr="value" 的元素。"""
    pat = re.compile(re.escape(attr) + r'="' + re.escape(value) + r'"')
    m = pat.search(h)
    if not m:
        return None
    # 往回找到元素起点
    lt = h.rfind("<", 0, m.start())
    if lt < 0:
        return None
    sp = elem_span(h, lt)
    if not sp:
        return None
    return (lt,) + sp


# ---------------------------------------------------------------- 标题/元信息

def page_title(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""


def h1_text(h):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    return one_line(m.group(1)) if m else ""


def ld_json(h):
    """抽取所有 application/ld+json。"""
    import json
    out = []
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
        try:
            out.append(json.loads(m.group(1).strip()))
        except Exception:
            pass
    return out


def meta_description(h):
    for d in ld_json(h):
        if isinstance(d, dict) and d.get("description"):
            return d["description"]
    m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', h)
    return unescape(m.group(1)) if m else ""
