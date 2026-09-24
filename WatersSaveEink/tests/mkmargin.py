# -*- coding: utf-8 -*-
"""生成「主页左右留白」改前/改后对照图（用带轮廓线的 ROI 截图）。"""
import os
from PIL import Image, ImageDraw, ImageFont

RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"
FONT = r"C:\Windows\Fonts\msyh.ttc"


def font(sz=15):
    try:
        return ImageFont.truetype(FONT, sz, index=0)
    except Exception:
        return ImageFont.load_default()


def load(name):
    return Image.open(os.path.join(RD, name + ".png")).convert("RGB").crop((0, 0, 1200, 825))


a = load("pre46roi")
b = load("v46roi")

SC = 0.66
tw, th = int(1200 * SC), int(825 * SC)
A = a.resize((tw, th), Image.LANCZOS)
B = b.resize((tw, th), Image.LANCZOS)

PAD, HDR, GAP = 12, 40, 10
W = tw + PAD * 2

# ---- 边缘放大条：左边缘 0..66px / 右边缘 1134..1200px，纵向取 240..460 ----
ZS = 3
zcrop = (240, 460)
zw = 66
zl_raw = (0, zcrop[0], zw, zcrop[1])
zr_raw = (1200 - zw, zcrop[0], 1200, zcrop[1])
zlw, zlh = zw * ZS, (zcrop[1] - zcrop[0]) * ZS
ZTITLE = 26
zrow_h = ZTITLE + zlh

H = HDR * 2 + th * 2 + PAD * 3 + GAP + zrow_h + 10
out = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(out)


def guides(y):
    for gx in (12, 1187):
        X = PAD + int(gx * SC)
        for yy in range(y, y + th, 6):
            d.line([(X, yy), (X, yy + 3)], fill=(235, 70, 0), width=1)


def caption(y, bg, lines):
    d.rectangle([0, y, W, y + HDR - 4], fill=bg)
    ty = y + 9
    for ln in lines:
        d.text((14, ty), ln, fill=(255, 255, 255), font=font(15))
        ty += 15


y1 = 0
caption(y1, (185, 28, 28), [
    "改前 (V3.2_759)：两栏贴着设备边缘铺满 —— 左栏轮廓线整个落在屏幕外被裁掉，左右留白 0px",
    "红框=左栏 .col-left    蓝框=右栏 .col-right    橙色竖虚线=12px / 1187px 参考线",
])
out.paste(A, (PAD, y1 + HDR))
guides(y1 + HDR)

y2 = HDR + th + GAP
caption(y2, (18, 125, 60), [
    "改后 (V3.3_760)：左右各让出 12px —— 左栏轮廓完整落在 x=9..11，右栏右界落在 x=1188..1190",
    "像素实测：左栏最外黑边 0px → 12px；右栏最右 1199px → 1188px；画布仍是 1200x825 没变",
])
out.paste(B, (PAD, y2 + HDR))
guides(y2 + HDR)

# ---- 第三行：左右边缘放大 3 倍对照 ----
y3 = y2 + HDR + th + PAD + 6
d.rectangle([0, y3, W, y3 + ZTITLE - 2], fill=(40, 40, 48))
d.text((14, y3 + 7), "边缘放大 3 倍（上：改前   下：改后）—— 白条宽度就是留白", fill=(255, 255, 255), font=font(15))
yy = y3 + ZTITLE
zorder = [("左边缘 0..66px", 0), ("右边缘 1134..1200px", 2)]
xcur = PAD
for label, gi in zorder:
    for im_src, tag in ((a, "改前"), (b, "改后")):
        box = zl_raw if gi == 0 else zr_raw
        strip = im_src.crop(box).resize((zlw, zlh), Image.NEAREST)
        out.paste(strip, (xcur, yy))
        d.rectangle([xcur, yy, xcur + zlw - 1, yy + zlh - 1], outline=(120, 120, 120))
        d.text((xcur + 4, yy + 4), "%s %s" % (label, tag), fill=(200, 0, 0), font=font(16))
        # 12px 参考线
        if gi == 0:
            X = xcur + 12 * ZS
        else:
            X = xcur + (1188 - 1134) * ZS
        d.line([(X, yy), (X, yy + zlh)], fill=(235, 70, 0), width=1)
        xcur += zlw + 8

dst = os.path.join(RD, "margin_compare.png")
out.save(dst)
print("wrote", dst, out.size)
