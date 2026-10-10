# -*- coding: utf-8 -*-
"""
从 美工/ 生成站点用图，输出到 site/assets/img/。

  logo.png / favicon.png   鱼形 logo（去掉白底、裁到内容、居中方形）
  venti.png                温迪 Q 版头像（每日一句的说话人头像）
  venti-banner.png         温迪青色横幅（首页 hero 的低透明度背景）

用法：python build_img.py（美工目录里的原图不动）
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(os.path.dirname(HERE), "美工")
OUT = os.path.join(HERE, "site", "assets", "img")


def trim_to_content(im, thr=246, keep_alpha=False):
    """裁到内容边界（并把接近白色的底变透明）。"""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > thr and g > thr and b > thr:
                if not keep_alpha and a > 0:
                    px[x, y] = (r, g, b, 0)
            else:
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

    # 1) logo：白底蓝鱼 -> 透明底方块
    src = os.path.join(ART, "1791647276381.png")
    if os.path.exists(src):
        im = trim_to_content(Image.open(src))
        square(im, 0.10, 256).save(os.path.join(OUT, "logo.png"))
        square(im, 0.10, 64).save(os.path.join(OUT, "favicon.png"))
        print("  logo.png / favicon.png  <- 1791647276381.png  %s" % (im.size,))
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
