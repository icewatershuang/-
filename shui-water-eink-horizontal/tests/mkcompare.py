# -*- coding: utf-8 -*-
"""Build a labelled before/after comparison PNG."""
from PIL import Image, ImageDraw, ImageFont
import os

RD = r"D:\workbuddy\2026-09-23-08-21-00\_render"
W, H = 980, 673          # 1200x825 scaled by 980/1200
BAR = 40


def load_font(size):
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def frame(name, caption, colour):
    im = Image.open(os.path.join(RD, name)).convert("RGB")
    im = im.crop((0, 0, 1200, 825)).resize((W, H), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H + BAR), "white")
    canvas.paste(im, (0, BAR))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, BAR - 1], fill=colour)
    d.text((10, 8), caption, font=load_font(22), fill="white")
    # guides: where the right column should end, and the page bottom
    d.line([(708 * W // 1200, BAR), (708 * W // 1200, BAR + H)], fill=(255, 0, 0), width=2)
    return canvas


a = frame("base_legacy_crop.png", "修改前：新闻标题冲出色栏 / 右栏 1080px", (180, 30, 30))
b = frame("orig_legacy_crop.png", "修改后：标题在栏内自动换行 / 右栏 708px", (20, 120, 40))

out = Image.new("RGB", (W, (H + BAR) * 2 + 10), "white")
out.paste(a, (0, 0))
out.paste(b, (0, H + BAR + 10))
p = os.path.join(RD, "compare.png")
out.save(p)
print(p, out.size, os.path.getsize(p))
