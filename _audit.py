# -*- coding: utf-8 -*-
"""审计：逐套列出各模块的实际内容量。"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'site', 'p')
DATA = os.path.join(HERE, 'data', 'paper')


def count(f, needle):
    if not os.path.exists(f):
        return -1
    return open(f, encoding='utf-8').read().count(needle)


print('%-12s %6s %6s | %6s %6s | %6s %6s | %s' % (
    'paper', 'cloze', 'bank', 'longP', 'longS', 'r1', 'r2', 'modules'))
for jf in sorted(glob.glob(os.path.join(DATA, '*.json'))):
    name = os.path.basename(jf)[:-5]
    d = json.load(open(jf, encoding='utf-8'))
    mods = d.get('modules', {})
    c = mods.get('cloze') or {}
    l = mods.get('longreading') or {}
    d1 = os.path.join(SITE, name)
    row = (
        len(c.get('passages') or []),
        len(c.get('wordbank') or []),
        len(l.get('passages') or []),
        len(l.get('statements') or []),
        count(os.path.join(d1, 'reading1.html'), 'data-qtype="choice"'),
        count(os.path.join(d1, 'reading2.html'), 'data-qtype="choice"'),
        ','.join(sorted(mods.keys())),
    )
    print('%-12s %6s %6s | %6s %6s | %6s %6s | %s' % ((name,) + row))
