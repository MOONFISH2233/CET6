# -*- coding: utf-8 -*-
"""生成站点的自检：题型完整性 + 顶栏链接的页面是否真的生成 + 重点词折叠块的位置。

历史上出过「page() 里写了 me.html / hfw.html 链接、但生成流程从没产出这两个页面」的
事，一直是 404 没人发现 —— 所以这里把页面存在性也纳入检查。
"""
import glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'site')


def scan(pattern, needle, need):
    bad, ok = [], 0
    files = sorted(glob.glob(pattern))
    for f in files:
        h = open(f, encoding='utf-8').read()
        n = h.count(needle)
        name = os.path.basename(os.path.dirname(f))
        if n < need:
            bad.append((name, n, len(h)))
        else:
            ok += 1
    print('%s: total=%d ok=%d bad=%d' % (pattern, len(files), ok, len(bad)))
    for b in bad:
        print('   BAD %-12s %s  size=%d' % b)
    return bad


def check_pages():
    """顶栏链接指着 me.html / hfw.html，这两个页面必须存在；兜底词库要有且别太胖。"""
    bad = []
    for fn in ('index.html', 'me.html', 'hfw.html'):
        p = os.path.join(SITE, fn)
        if os.path.exists(p):
            print('  %-10s %d bytes' % (fn, os.path.getsize(p)))
        else:
            print('  %-10s MISSING' % fn)
            bad.append(fn)
    da = os.path.join(SITE, 'dict_all.json')
    if not os.path.exists(da):
        print('  dict_all.json MISSING（word.js 会退化成「未收录」）')
        bad.append('dict_all.json')
    else:
        kb = os.path.getsize(da) // 1024
        flag = 'OK' if kb < 4096 else '过大'
        print('  dict_all.json %d KB  %s' % (kb, flag))
        if kb >= 4096:
            bad.append('dict_all.json 体积')
    return bad


def check_hfw_card():
    """有词表的套应带重点词折叠块，没词表的不该带（免得空白卡片 + 404 请求）。"""
    have = {f[:-5] for f in os.listdir(os.path.join(HERE, 'data', 'hfw')) if f.endswith('.json')}
    bad = 0
    for m in ('listening', 'cloze', 'longreading', 'reading1', 'reading2'):
        files = sorted(glob.glob(os.path.join(SITE, 'p', '*', m + '.html')))
        wrong = []
        for f in files:
            s = os.path.basename(os.path.dirname(f))
            has = 'hfw-card' in open(f, encoding='utf-8').read()
            if has != (s in have):
                wrong.append(s)
        print('  %-12s %3d 页 · 与词表不符 %d %s' % (m, len(files), len(wrong), wrong[:3]))
        bad += len(wrong)
    for m in ('writing', 'translation'):
        files = glob.glob(os.path.join(SITE, 'p', '*', m + '.html'))
        extra = [os.path.basename(os.path.dirname(f)) for f in files
                 if 'hfw-card' in open(f, encoding='utf-8').read()]
        if extra:
            print('  %-12s 不该有折叠块，却有 %d 页' % (m, len(extra)))
            bad += len(extra)
    return bad


def check_audio():
    """有音频的套：听力页必须带播放器，而且每道题都要有「听这题」。

    历史上吃过「以为加了其实没落地」的亏，所以这里把音频也纳入自检。
    """
    adir = os.path.join(SITE, 'audio')
    if not os.path.isdir(adir):
        print('  site/audio 不存在（还没跑 build_audio.py），跳过')
        return 0
    sets = sorted(f[:-4] for f in os.listdir(adir) if f.endswith('.mp3'))
    print('  有音频 %d 套: %s' % (len(sets), ' '.join(sets[:4]) + (' …' if len(sets) > 4 else '')))
    bad = 0
    for s in sets:
        f = os.path.join(SITE, 'p', s, 'listening.html')
        if not os.path.exists(f):
            print('    BAD %s 没有听力页' % s)
            bad += 1
            continue
        h = open(f, encoding='utf-8').read()
        n_q = h.count('class="aud-q"')
        need = len([1 for _ in __import__('re').finditer(r'data-qno=', h)])
        if 'audPlayer' not in h or n_q < need:
            print('    BAD %s 播放器=%s 听这题=%d/%d' % (s, 'audPlayer' in h, n_q, need))
            bad += 1
    if not bad:
        print('    每套都有播放器，且每题都有「听这题」')
    return bad


if __name__ == '__main__':
    b1 = scan(os.path.join(SITE, 'p', '*', 'cloze.html'), 'cslot', 10)
    b2 = scan(os.path.join(SITE, 'p', '*', 'longreading.html'), 'data-qtype="match"', 10)
    b3 = scan(os.path.join(SITE, 'p', '*', 'reading1.html'), 'data-qtype="choice"', 5)
    print('独立页面:')
    b4 = check_pages()
    print('重点词折叠块:')
    b5 = check_hfw_card()
    print('听力音频:')
    b6 = check_audio()
    sys.exit(1 if (b1 or b2 or b3 or b4 or b5 or b6) else 0)
