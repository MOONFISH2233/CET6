# -*- coding: utf-8 -*-
"""
把听力音频抓下来，转成站点能直接播的 mp3。

源：懒笔记的听力页里，<audio> 的 src 指向 HLS 流
      https://listening.lazynote.cn/cet6/<id>/index.m3u8   （标准 VOD 清单，无签名）
    实测：m3u8 与 .ts 分片都能直连下载（HTTP 200）。

产物：
    site/audio/<set>.mp3        48kbps 单声道，27 分钟约 10MB；preload=none，不点不下载
    data/audio_src/<set>.json   从源页抓的每篇区间 {label, start, end, anchor}，
                                供 gen_site 做「跳到第 N 篇」「听这题」的定位

用法：
    python build_audio.py                 # 计划要用的 10 套
    python build_audio.py 2024-06-1 ...   # 指定套次
    python build_audio.py --force         # 重下（忽略已有 mp3）
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SITE_AUDIO = os.path.join(HERE, "site", "audio")
SRC_META = os.path.join(DATA, "audio_src")
CACHE = os.path.join(HERE, "_cache", "audio")     # ts 分片缓存（不进仓库）

SRC = "https://english-exam.lazynote.cn/cet6/sections/listening/%s/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

# 打卡站 61 天里真正会听到的：2023-06 ~ 2025-06 的第 1、2 套（第 3 套源站没听力）
PLAN_SETS = ["2023-06-1", "2023-06-2", "2023-12-1", "2023-12-2",
             "2024-06-1", "2024-06-2", "2024-12-1", "2024-12-2",
             "2025-06-1", "2025-06-2"]


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_page(setname):
    """源听力页 HTML（小，几十 KB 就够；整页 780KB 也还行）"""
    return get(SRC % setname).decode("utf-8", "replace")


def scrap(setname):
    """从源页抓：音频 id + 每篇区间。返回 dict 或 None"""
    html = fetch_page(setname)
    m = re.search(r'(https://listening\.lazynote\.cn/cet6/\d+/index\.m3u8)', html)
    if not m:
        return None
    m3u8 = m.group(1)
    aid = re.search(r'/cet6/(\d+)/', m3u8).group(1)

    # astro-island 把播放数据放在 props 属性里（[type, value] 编码）
    pieces = []
    im = re.search(r'component-url="[^"]*ListeningAudioBar[^"]*"[^>]*props="([^"]*)"', html)
    if not im:
        im = re.search(r'props="([^"]*)"[^>]*component-url="[^"]*ListeningAudioBar', html)
    if im:
        raw = im.group(1)
        # HTML 实体还原
        for a, b in (("&quot;", '"'), ("&amp;", "&"), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
            raw = raw.replace(a, b)
        # props 是 Astro 的 [type, value] 编码，套嵌好几层。
        # 不折腾解码了：label/start/end/anchor 在串里是**顺序成对**出现的，直接按序抠。
        labs = re.findall(r'"label":\[0,"([^"]*)"\]', raw)
        starts = [float(x) for x in re.findall(r'"start":\[0,([\d.]+)\]', raw)]
        ends = [float(x) for x in re.findall(r'"end":\[0,([\d.]+)\]', raw)]
        anchs = re.findall(r'"anchor":\[0,"([^"]*)"\]', raw)
        if labs and len(labs) == len(starts) == len(ends):
            for i, lab in enumerate(labs):
                pieces.append({
                    "label": lab,
                    "anchor": anchs[i] if i < len(anchs) else "",
                    "start": starts[i],
                    "end": ends[i],
                })
        else:
            print("    ! 区间抠取不齐: label=%d start=%d end=%d" % (len(labs), len(starts), len(ends)))

    return {"set": setname, "audio_id": aid, "m3u8": m3u8, "pieces": pieces}


def fetch_m3u8(url):
    text = get(url).decode("utf-8", "replace")
    segs = re.findall(r'^([^\s#].*\.ts)\s*$', text, re.M)
    total = sum(float(x) for x in re.findall(r'#EXTINF:([\d.]+)', text))
    return segs, total


def download_ts(base, seg, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "cached"
    data = get(base + seg, timeout=90)
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, dest)
    return "ok"


def build_set(info, force=False):
    setname, m3u8 = info["set"], info["m3u8"]
    out_mp3 = os.path.join(SITE_AUDIO, setname + ".mp3")
    if os.path.exists(out_mp3) and not force:
        print("  %-12s 已有 mp3，跳过（--force 可重下）" % setname)
        return True

    base = m3u8.rsplit("/", 1)[0] + "/"
    segs, total = fetch_m3u8(m3u8)
    print("  %-12s id=%s · %d 个分片 · %.1f 分钟" % (setname, info["audio_id"], len(segs), total / 60))

    cdir = os.path.join(CACHE, setname)
    os.makedirs(cdir, exist_ok=True)
    os.makedirs(SITE_AUDIO, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda s: download_ts(base, s, os.path.join(cdir, s)), segs))

    # 分片按名字排序就是播放顺序（s_000, s_001 …）
    order = sorted(segs)
    listfile = os.path.join(cdir, "_list.txt")
    with open(listfile, "w", encoding="utf-8") as f:
        for s in order:
            f.write("file '%s'\n" % os.path.join(cdir, s).replace("\\", "/"))

    tmp_out = out_mp3 + ".tmp.mp3"
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", listfile,
           "-vn", "-ac", "1", "-ar", "24000", "-b:a", "48k",
           "-write_xing", "1",          # 有 Xing 头，浏览器不用下完整个文件就能拖动
           tmp_out]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("    ! ffmpeg 失败: " + r.stderr.decode("utf-8", "replace")[:400])
        return False
    os.replace(tmp_out, out_mp3)
    mb = os.path.getsize(out_mp3) / 1024 / 1024
    print("    → %s  %.1f MB  (%.0fs)" % (os.path.basename(out_mp3), mb, total))
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    sets = args or PLAN_SETS

    os.makedirs(SRC_META, exist_ok=True)
    ok = 0
    for s in sets:
        print("== %s ==" % s)
        try:
            info = scrap(s)
        except Exception as e:
            print("  ! 抓源页失败: %s" % e)
            continue
        if not info:
            print("  ! 源页没有音频（这套大概没听力）")
            continue
        with open(os.path.join(SRC_META, s + ".json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
        print("    每篇区间: " + " · ".join(
            "%s %.1f–%.1f" % (p["label"].split(" · ")[-1], p["start"], p["end"])
            for p in info["pieces"]) if info["pieces"] else "    （没抓到区间）")
        try:
            if build_set(info, force):
                ok += 1
        except Exception as e:
            print("  ! 下载/转码失败: %s" % e)

    total = 0
    if os.path.isdir(SITE_AUDIO):
        for fn in os.listdir(SITE_AUDIO):
            total += os.path.getsize(os.path.join(SITE_AUDIO, fn))
    print("\n完成 %d/%d 套 · site/audio 合计 %.1f MB" % (ok, len(sets), total / 1024 / 1024))


if __name__ == "__main__":
    main()
