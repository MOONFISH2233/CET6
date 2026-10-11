# -*- coding: utf-8 -*-
"""
从 美工/ 生成站点用图，输出到 site/assets/img/。

  logo.png / favicon.png   鱼形 logo（去掉白底、裁到内容、居中方形）
  venti.png                温迪 Q 版头像（每日一句的说话人头像）
  venti-banner.png         温迪青色横幅（首页 hero 的低透明度背景）

用法：python build_img.py（美工目录里的原图不动）
"""
import io
import os
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(os.path.dirname(HERE), "美工")
OUT = os.path.join(HERE, "site", "assets", "img")


def cutout_line_art(im, lo=20, hi=60):
    """把白底线条图抠成透明底，并裁到内容边界。

    这张 logo 的白底上还压着一层很淡的蓝色水彩云（RGB 差 5~30），只按「接近白色」判断
    抠不干净。改成按**色彩饱和度**（max-min 通道差）做蒙版：
      差 ≥ hi  → 实心线条；差 ≤ lo → 全透明（白底 + 淡云一起去掉）；中间按比例渐变，保住边缘抗锯齿。
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            sp = max(r, g, b) - min(r, g, b)
            if sp <= lo:
                alpha = 0
            elif sp >= hi:
                alpha = 255
            else:
                alpha = int((sp - lo) * 255 / (hi - lo))
            px[x, y] = (r, g, b, alpha)
            if alpha > 8:
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if maxx < 0:
        return im
    return im.crop((minx, miny, maxx + 1, maxy + 1))


def square(im, pad=0.12, size=256):
    """补成正方形（留一点边距）再缩放。"""
    w, h = im.size
    side = int(max(w, h) * (1 + pad * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    return canvas.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "gallery"), exist_ok=True)

    # 0.5) 收藏墙缩略图：240×240 方图（高的图往上取，别切掉头）
    #      文件名映射：见 gen_site.GALLERY（谁是谁由用户 2026-10-11 指认）
    GALLERY = [
        ("venti-1.jpg", "温迪抽卡立绘.png", "温迪 · 抽卡"),
        ("venti-2.jpg", "温迪立绘.png", "温迪 · 立绘"),
        ("venti-3.jpg", "温迪_立绘.png", "温迪 · 立绘"),
        ("venti-4.jpg", "温迪立绘2.png", "温迪 · 立绘"),
        ("venti-5.jpg", "温迪_天青.png", "温迪 · 天青"),
        ("venti-6.jpg", "温迪官方故事图.png", "温迪 · 角色故事"),
        ("pyx-1.jpg", "Image_1791658697127_390.jpg", "蒲熠星"),
        ("pyx-2.jpg", "Image_1791658701796_841.jpg", "蒲熠星"),
        ("pyx-3.jpg", "Image_1791658703827_905.jpg", "蒲熠星"),
        ("pyx-4.jpg", "Image_1791658715343_253.jpg", "蒲熠星"),
        ("sll-1.jpg", "Camera_XHS_1791658626377.jpg", "孙路路"),
        ("sll-2.jpg", "Camera_XHS_1791658622329notes_uhdr_1040g3qg31oug3tvrgu005o1jc4mgboiv0pib2t8.jpg", "孙路路"),
        ("sll-3.jpg", "Camera_XHS_17916585922751040g008325rsnr054c105o1jc4mgboivqs8clrg.jpg", "孙路路"),
        ("sll-4.jpg", "Image_1791658731396_864.jpg", "孙路路"),
    ]
    made = []
    for out_name, src_name, cap in GALLERY:
        p = os.path.join(ART, src_name)
        if not os.path.exists(p):
            continue
        im = Image.open(p)
        if im.mode in ("RGBA", "LA", "P"):
            # 透明底压到浅灰上（深色模式里就像一张浅色照片，不难看）
            bg = Image.new("RGB", im.size, (241, 240, 239))
            im = im.convert("RGBA")
            bg.paste(im, (0, 0), im)
            im = bg
        else:
            im = im.convert("RGB")
        im = ImageOps.fit(im, (240, 240), Image.LANCZOS, centering=(0.5, 0.28))
        im.save(os.path.join(OUT, "gallery", out_name), quality=78, optimize=True)
        made.append((out_name, cap))
    kb = sum(os.path.getsize(os.path.join(OUT, "gallery", n)) for n, _ in made) / 1024
    print("  收藏墙缩略图 %d 张 · 共 %.0f KB" % (len(made), kb))
    # 清单给 gen_site.build_me 读，免得两边各维护一份文件名
    import json
    with io.open(os.path.join(OUT, "gallery", "index.json"), "w", encoding="utf-8") as f:
        json.dump([{"f": n, "cap": c} for n, c in made], f, ensure_ascii=False, indent=1)

    # 0) 说话人头像：从本人照片裁头肩方图（文件名映射由用户 2026-10-11 指认）
    #    Image_17916587{26,29,31}* + Camera_XHS_* = 孙路路；Image_17916587{18,23,69,70,71}* = 蒲熠星
    AVATARS = [
        ("sll.jpg", "Camera_XHS_1791658626377.jpg", (650, 210, 1130, 690)),
        ("pyx.jpg", "Image_1791658697127_390.jpg", (555, 930, 985, 1360)),
    ]
    for out_name, src_name, box in AVATARS:
        p = os.path.join(ART, src_name)
        if not os.path.exists(p):
            print("  缺 %s，跳过 %s" % (src_name, out_name))
            continue
        im = Image.open(p).convert("RGB").crop(box).resize((192, 192), Image.LANCZOS)
        im.save(os.path.join(OUT, out_name), quality=88, optimize=True)
        print("  %-9s <- %s %s" % (out_name, src_name[:28], box))

    # 1) logo：白底蓝鱼 -> 透明底方块（按饱和度抠掉白底和那层淡蓝水彩云）
    src = os.path.join(ART, "1791647276381.png")
    if os.path.exists(src):
        im = cutout_line_art(Image.open(src))
        square(im, 0.10, 256).save(os.path.join(OUT, "logo.png"))
        square(im, 0.10, 64).save(os.path.join(OUT, "favicon.png"))
        print("  logo.png / favicon.png  <- 1791647276381.png  裁后 %s" % (im.size,))
        # 预览：分别压在浅色/深色底上看抠得干不干净
        for name, bg in (("_preview-light", (247, 247, 245)), ("_preview-dark", (22, 23, 26))):
            canvas = Image.new("RGB", (256, 256), bg)
            logo = square(im, 0.10, 256)
            canvas.paste(logo, (0, 0), logo)
            canvas.save(os.path.join(OUT, name + ".png"))
    else:
        print("  缺 %s，跳过 logo" % src)

    # 2) 温迪 Q 版头像
    src = os.path.join(ART, "温迪头像.png")
    if os.path.exists(src):
        im = Image.open(src).convert("RGBA").resize((96, 96), Image.LANCZOS)
        im.save(os.path.join(OUT, "venti.png"))
        print("  venti.png  96x96")
    else:
        print("  缺 %s，跳过温迪头像" % src)

    # 2.5) 温迪抽卡立绘（宽幅）做 hero 装饰底图，压到 1000 宽
    src = os.path.join(ART, "温迪抽卡立绘.png")
    if os.path.exists(src):
        im = Image.open(src).convert("RGB")
        w, h = im.size
        im = im.resize((1000, int(h * 1000 / w)), Image.LANCZOS)
        im.save(os.path.join(OUT, "venti-splash.jpg"), quality=76, optimize=True)
        print("  venti-splash.jpg  %s  %.0f KB" % (
            im.size, os.path.getsize(os.path.join(OUT, "venti-splash.jpg")) / 1024))
    else:
        print("  缺 %s，跳过抽卡立绘" % src)

    # 3) 温迪青色横幅（hero 背景，压到 720 宽）
    src = os.path.join(ART, "温迪_天青.png")
    if os.path.exists(src):
        im = Image.open(src).convert("RGB")
        w, h = im.size
        im = im.resize((720, int(h * 720 / w)), Image.LANCZOS)
        im.save(os.path.join(OUT, "venti-banner.jpg"), quality=82, optimize=True)
        print("  venti-banner.jpg  %s  %.0f KB" % (
            im.size, os.path.getsize(os.path.join(OUT, "venti-banner.jpg")) / 1024))
    else:
        print("  缺 %s，跳过横幅" % src)

    print("\n输出: " + OUT)


if __name__ == "__main__":
    main()
    sys.exit(0)
