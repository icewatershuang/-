# -*- coding: utf-8 -*-
"""给夹具注入临时轮廓线（只影响测试页，不进产物），再截图并量出栏边界。"""
import io, os, re, sys
from PIL import Image, ImageDraw

sys.path.insert(0, r"D:\workbuddy\2026-09-23-08-21-00")
import _shot  # noqa: E402

RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"

ROI = (
    '<style id="harnessRoi">'
    '/* 仅测试页：给两栏描边，方便用像素量出左右边界 */'
    '.col-left{outline:3px solid #d81b1b !important;}'
    '.col-right{outline:3px solid #1240c8 !important;}'
    '</style>'
)


def make(name):
    src = os.path.join(RD, name + ".html")
    html = io.open(src, encoding="utf-8").read()
    hd = html.rfind("</head>")
    html = html[:hd] + ROI + html[hd:]
    out = os.path.join(RD, name + "roi.html")
    io.open(out, "w", encoding="utf-8").write(html)
    return name + "roi"


def find_color_cols(name, rgb, tol=60):
    im = Image.open(os.path.join(RD, name + ".png")).convert("RGB").crop((0, 0, 1200, 825))
    px = im.load()
    cols = []
    for x in range(1200):
        n = 0
        for y in range(0, 825, 2):
            r, g, b = px[x, y]
            if abs(r - rgb[0]) < tol and abs(g - rgb[1]) < tol and abs(b - rgb[2]) < tol:
                n += 1
        if n >= 40:
            cols.append(x)
    return cols


if __name__ == "__main__":
    for base in ("pre46", "v46"):
        n = make(base)
        _shot.shot(n)
        red = find_color_cols(n, (216, 27, 27))
        blue = find_color_cols(n, (18, 64, 200))
        print("%-12s 左栏(红)列范围=%s..%s   右栏(蓝)列范围=%s..%s"
              % (base,
                 red[0] if red else "-", red[-1] if red else "-",
                 blue[0] if blue else "-", blue[-1] if blue else "-"))
