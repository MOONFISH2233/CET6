# -*- coding: utf-8 -*-
import re, io, sys

path = r"D:\学习\六级\build\site\p\2023-06-1\listening.html"
with io.open(path, "r", encoding="utf-8") as f:
    html = f.read()

print("=== 文件长度:", len(html))

# 1) 找出所有 26~35 的题号锚点 / 相关区块
print("\n=== 1) 搜索 '26'~'35' 作为题号出现的位置 ===")
for n in range(26, 36):
    # 匹配形如 >26< 或 question-number 之类
    pats = [
        r'>\s*%d\s*<' % n,
        r'data-q="%d"' % n,
        r'id="q%d"' % n,
        r'\b%d\.' % n,
    ]
    hits = []
    for p in pats:
        for m in re.finditer(p, html):
            hits.append((p, m.start()))
    print("Q%d: %d 处命中 %s" % (n, len(hits), hits[:3]))

# 2) 查找空号相关标记（placeholder / blank / 空 / ____）
print("\n=== 2) 空号占位符统计 ===")
for kw in ["____", "blank", "placeholder", "空号", "未作答", "unanswered", "no-answer", "missing"]:
    c = html.count(kw)
    if c:
        print("  %-14s : %d" % (kw, c))

# 3) 查找底部答案栏区块
print("\n=== 3) 答案栏/答案区相关标记 ===")
for kw in ["answer", "答案", "ansBtn", "ans-", "key-", "correct"]:
    c = html.lower().count(kw.lower())
    if c:
        print("  %-12s : %d" % (kw, c))

# 4) 提取答案区附近内容（找包含 26~35 的表格/列表）
print("\n=== 4) 提取含 '26' 的答案行（前后 200 字符）===")
idx = 0
cnt = 0
while True:
    idx = html.find("26", idx + 1)
    if idx == -1 or cnt >= 8:
        break
    seg = html[max(0, idx-80):idx+120].replace("\n", " ")
    # 只保留看起来像答案栏的段
    if any(k in seg.lower() for k in ["answer", "答案", "key", "correct", "q26", ">26<"]):
        print("  ...", seg, "...")
        cnt += 1

# 5) 检查 26~35 是否成对出现在答案栏（如 "26": "A"）
print("\n=== 5) 答案对（数字+选项字母）匹配 ===")
pair = re.findall(r'(\d{1,2})\s*[：:]\s*([A-D])', html)
pair += re.findall(r'"?(\d{1,2})"?\s*[=>:]\s*"([A-D])"', html)
print("  找到 %d 组 (题号:选项)" % len(pair))
for q, a in pair:
    if 26 <= int(q) <= 35:
        print("    Q%s -> %s" % (q, a))

print("\n=== 完成 ===")
