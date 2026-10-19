"""Profilbild (800x800) und Banner (2560x1440) im Look der Shorts."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from make_short import grade, font, GOLD, WHITE

SRC = os.path.expanduser("~/rubic-cache/photos/u_skcFiBu91AA.jpg")   # Milchstraße aus den Videos
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp"


def cover(img, w, h, fx=0.5, fy=0.5, zoom=1.0):
    iw, ih = img.size
    s = max(w / iw, h / ih) * zoom
    img = img.resize((math.ceil(iw * s), math.ceil(ih * s)), Image.LANCZOS)
    x, y = int((img.width - w) * fx), int((img.height - h) * fy)
    return img.crop((x, y, x + w, y + h))


def finish(img, vig=0.40, grain=0.03, seed=7):
    a = np.asarray(img.convert("RGB"), np.float32)
    h, w = a.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    a *= (1 - vig * np.clip((r - 0.25) / 0.75, 0, 1) ** 1.6)[..., None]
    g = np.random.default_rng(seed).normal(0, grain * 255, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[:h, :w]
    a = np.clip(a + g[..., None], 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def text_with_shadow(img, parts, size, center, blur=18, line2=None, size2=None):
    """parts: [(text, color)] in einer Zeile, zentriert um center."""
    f = font(size)
    total = sum(f.getlength(t) for t, _ in parts)
    x0 = center[0] - total / 2
    y0 = center[1] - size * 0.62
    mask = Image.new("L", img.size, 0)
    col = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dm, dc = ImageDraw.Draw(mask), ImageDraw.Draw(col)
    x = x0
    for t, c in parts:
        dm.text((x, y0), t, font=f, fill=255)
        dc.text((x, y0), t, font=f, fill=c + (255,))
        x += f.getlength(t)
    if line2:
        f2 = font(size2)
        w2 = f2.getlength(line2)
        y2 = y0 + size * 1.25
        dm.text((center[0] - w2 / 2, y2), line2, font=f2, fill=230)
        dc.text((center[0] - w2 / 2, y2), line2, font=f2, fill=(255, 255, 255, 225))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * 0.8)))
    sh = sh.transform(img.size, Image.AFFINE, (1, 0, 0, 0, 1, -6))
    return Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), sh), col)


src = Image.open(SRC)

# Banner: 2560x1440, sicherer Bereich in der Mitte 1546x423
ban = grade(cover(src, 2560, 1440, fy=0.45))
ban = finish(ban, vig=0.40)
ban = text_with_shadow(ban, [("Steine", GOLD), (". Und die vier Elemente.", WHITE)], 104, (1280, 690),
                       line2="Feuer · Wasser · Erde · Wind", size2=52)
ban.convert("RGB").save(os.path.join(OUT, "rubic-banner.png"))

# Profilbild: 800x800, rund beschnitten bei YouTube → Inhalt mittig
pro = grade(cover(src, 800, 800, fx=0.55, fy=0.4, zoom=1.15))
pro = finish(pro, vig=0.45)
pro = text_with_shadow(pro, [("R", GOLD)], 430, (400, 420), blur=24)
pro.convert("RGB").save(os.path.join(OUT, "rubic-profil.png"))
print("ok")
