# -*- coding: utf-8 -*-
"""
KT Delay GUI image generator.
Copyright (c) 2026 aike. SPDX-License-Identifier: MIT
Generates:
  resource/background.png  (600 x 260)   editor background
  resource/knob.png        (80 x 8080)   film strip, 101 frames of 80x80 (vertical)
  resource/bypass.png      (96 x 68)     2 frames of 96x34 (top = off, bottom = on)
  resource/<UID>_snapshot.png            plugin snapshot for hosts
  resource/preview.png                   composite preview of the editor
Run:  python tools/gen_images.py
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resource")
os.makedirs(OUT, exist_ok=True)

W, H = 600, 260
KNOB = 80
FRAMES = 101
SS = 4                      # supersampling factor
KNOB_Y = 100
KNOB_XS = [55, 195, 335, 475]       # left edges (centers at 95/235/375/515)
LABELS = ["DELAY TIME", "FEEDBACK", "WET LEVEL", "DUCKING"]
BYPASS_W, BYPASS_H = 96, 34
BYPASS_POS = (480, 22)
PROCESSOR_UID = "E4B7EC890B0F489DB6EE9737C605845F"

ACCENT = (242, 163, 60)      # amber
TXT = (214, 216, 222)
TXT_DIM = (130, 134, 142)


def font(size, bold=False):
    cands = (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"])
    for c in cands:
        for d in [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"]:
            p = os.path.join(d, c)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------------------------------------------------------------- background
def make_background():
    img = Image.new("RGB", (W, H))
    px = img.load()
    top, bot = (46, 49, 56), (24, 26, 30)
    for y in range(H):
        c = lerp(top, bot, y / (H - 1))
        for x in range(W):
            px[x, y] = c
    # subtle brushed-metal horizontal streaks
    random.seed(7)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 2):
        v = random.randint(-4, 4)
        base = px[0, y]
        d.line([(0, y), (W, y)], fill=tuple(max(0, min(255, base[i] + v)) for i in range(3)))

    # header bar separator
    d.line([(0, 66), (W, 66)], fill=(16, 17, 20))
    d.line([(0, 67), (W, 67)], fill=(70, 74, 82))

    # title
    d.text((24, 14), "KT DELAY", font=font(30, True), fill=TXT)
    d.text((26, 46), "STEREO DUCKING DELAY", font=font(11), fill=TXT_DIM)
    d.rectangle([(14, 18), (18, 56)], fill=ACCENT)

    # knob panel (slightly darker, rounded)
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    pd.rounded_rectangle([(20, 80), (W - 20, H - 16)], radius=10,
                         fill=(0, 0, 0, 55), outline=(90, 94, 102, 120))
    img = Image.alpha_composite(img.convert("RGBA"), panel)

    # tick scales around knobs (supersampled) + labels
    scale = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scale)
    for i, x in enumerate(KNOB_XS):
        cx, cy = x + KNOB / 2, KNOB_Y + KNOB / 2
        r_in, r_out = 44 * SS, 49 * SS
        for k in range(11):
            a = math.radians(135 + 270 * k / 10)
            r2 = r_out + (3 * SS if k in (0, 5, 10) else 0)
            x0, y0 = cx * SS + r_in * math.cos(a), cy * SS + r_in * math.sin(a)
            x1, y1 = cx * SS + r2 * math.cos(a), cy * SS + r2 * math.sin(a)
            sd.line([(x0, y0), (x1, y1)], fill=(170, 174, 182, 200), width=SS + 1)
    scale = scale.resize((W, H), Image.LANCZOS)
    img = Image.alpha_composite(img, scale)
    d = ImageDraw.Draw(img)
    f = font(12, True)
    for i, x in enumerate(KNOB_XS):
        cx = x + KNOB / 2
        tw = d.textlength(LABELS[i], font=f)
        d.text((cx - tw / 2, KNOB_Y + KNOB + 20), LABELS[i], font=f, fill=TXT)

    # min/max hints for delay time
    f = font(9)
    d.text((KNOB_XS[0] - 2, KNOB_Y + KNOB - 4), "0", font=f, fill=TXT_DIM)
    d.text((KNOB_XS[0] + KNOB - 14, KNOB_Y + KNOB - 4), "400", font=f, fill=TXT_DIM)

    # footer
    d.text((W - 96, H - 14), "v1.0  aikelab", font=font(9), fill=(90, 94, 102))

    img = img.convert("RGB")
    img.save(os.path.join(OUT, "background.png"))
    return img


# ---------------------------------------------------------------- knob strip
def draw_knob_frame(t):
    """t: 0..1 normalized value. returns 80x80 RGBA image"""
    S = KNOB * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c = S / 2
    start, sweep = 135, 270              # degrees, PIL: 0 = 3 o'clock, clockwise
    ang = start + sweep * t

    # drop shadow
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sdr = ImageDraw.Draw(sh)
    sdr.ellipse([c - 30 * SS, c - 28 * SS, c + 30 * SS, c + 34 * SS], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(3 * SS))
    img = Image.alpha_composite(img, sh)
    d = ImageDraw.Draw(img)

    # value arc track (dim) and lit arc
    bbox = [c - 37 * SS, c - 37 * SS, c + 37 * SS, c + 37 * SS]
    d.arc(bbox, start, start + sweep, fill=(60, 63, 70, 255), width=int(3.5 * SS))
    if t > 0.002:
        d.arc(bbox, start, ang, fill=ACCENT + (255,), width=int(3.5 * SS))

    # outer bezel ring
    R = 31 * SS
    for k, col in enumerate([(22, 23, 27), (58, 61, 68), (38, 40, 46)]):
        rr = R - k * 1.2 * SS
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=col + (255,))

    # knob body: radial gradient (lighter top-left)
    body_r = 27 * SS
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bp = body.load()
    lx, ly = c - body_r * 0.45, c - body_r * 0.55
    for y in range(int(c - body_r) - 1, int(c + body_r) + 2):
        for x in range(int(c - body_r) - 1, int(c + body_r) + 2):
            dx, dy = x - c, y - c
            dist = math.hypot(dx, dy)
            if dist <= body_r:
                dl = math.hypot(x - lx, y - ly) / (2.0 * body_r)
                v = max(0.0, 1.0 - dl)
                base = lerp((48, 51, 58), (96, 100, 110), v)
                e = dist / body_r
                if e > 0.85:
                    base = lerp(base, (30, 31, 36), (e - 0.85) / 0.15)
                bp[x, y] = base + (255,)
    img = Image.alpha_composite(img, body)
    d = ImageDraw.Draw(img)

    # pointer
    a = math.radians(ang)
    r0, r1 = 9 * SS, 24 * SS
    x0, y0 = c + r0 * math.cos(a), c + r0 * math.sin(a)
    x1, y1 = c + r1 * math.cos(a), c + r1 * math.sin(a)
    d.line([(x0, y0), (x1, y1)], fill=(20, 20, 24, 200), width=int(4.5 * SS))
    d.line([(x0, y0), (x1, y1)], fill=(240, 242, 246, 255), width=int(2.6 * SS))
    d.ellipse([x1 - 1.6 * SS, y1 - 1.6 * SS, x1 + 1.6 * SS, y1 + 1.6 * SS], fill=ACCENT + (255,))

    # top highlight
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([c - 20 * SS, c - 24 * SS, c + 14 * SS, c - 4 * SS], fill=(255, 255, 255, 28))
    hl = hl.filter(ImageFilter.GaussianBlur(2 * SS))
    img = Image.alpha_composite(img, hl)

    return img.resize((KNOB, KNOB), Image.LANCZOS)


def make_knob_strip():
    strip = Image.new("RGBA", (KNOB, KNOB * FRAMES), (0, 0, 0, 0))
    frames = []
    for i in range(FRAMES):
        fr = draw_knob_frame(i / (FRAMES - 1))
        frames.append(fr)
        strip.paste(fr, (0, i * KNOB))
    strip.save(os.path.join(OUT, "knob.png"))
    return frames


# ---------------------------------------------------------------- bypass button
def draw_bypass(on):
    S = SS
    w, h = BYPASS_W * S, BYPASS_H * S
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body_fill = (40, 42, 48, 255) if not on else (52, 46, 40, 255)
    d.rounded_rectangle([(0.5 * S, 0.5 * S), (w - 0.5 * S, h - 0.5 * S)], radius=7 * S,
                        fill=body_fill, outline=(14, 15, 18, 255), width=S)
    d.rounded_rectangle([(1.5 * S, 1.5 * S), (w - 1.5 * S, h - 1.5 * S)], radius=6 * S,
                        outline=(84, 88, 96, 255) if not on else (120, 100, 70, 255), width=S)
    # LED
    lx, ly, lr = 15 * S, h / 2, 5 * S
    if on:
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse([lx - lr * 2.2, ly - lr * 2.2, lx + lr * 2.2, ly + lr * 2.2], fill=ACCENT + (140,))
        glow = glow.filter(ImageFilter.GaussianBlur(2.5 * S))
        img = Image.alpha_composite(img, glow)
        d = ImageDraw.Draw(img)
        d.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(255, 196, 96, 255),
                  outline=(120, 80, 30, 255), width=S)
        d.ellipse([lx - lr * 0.45, ly - lr * 0.7, lx + lr * 0.25, ly - lr * 0.05],
                  fill=(255, 240, 210, 255))
    else:
        d.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], fill=(70, 56, 40, 255),
                  outline=(20, 20, 24, 255), width=S)
    # text
    f = font(13 * S, True)
    txt = "BYPASS"
    tw = d.textlength(txt, font=f)
    tx = 28 * S + (w - 28 * S - tw) / 2 - 4 * S
    d.text((tx, (h - 13 * S) / 2 - 2 * S), txt, font=f, fill=(TXT if on else TXT_DIM) + (255,))
    return img.resize((BYPASS_W, BYPASS_H), Image.LANCZOS)


def make_bypass():
    off, on = draw_bypass(False), draw_bypass(True)
    img = Image.new("RGBA", (BYPASS_W, BYPASS_H * 2), (0, 0, 0, 0))
    img.paste(off, (0, 0))
    img.paste(on, (0, BYPASS_H))
    img.save(os.path.join(OUT, "bypass.png"))
    return off


# ---------------------------------------------------------------- snapshot
def make_snapshot(bg, frames, bypass_off):
    img = bg.convert("RGBA")
    defaults = [250 / 400, 0.30, 0.50, 0.0]
    for x, v in zip(KNOB_XS, defaults):
        fr = frames[int(round(v * (FRAMES - 1)))]
        img.alpha_composite(fr, (x, KNOB_Y))
    img.alpha_composite(bypass_off, BYPASS_POS)
    img.convert("RGB").save(os.path.join(OUT, PROCESSOR_UID + "_snapshot.png"))
    img.convert("RGB").save(os.path.join(OUT, "preview.png"))


if __name__ == "__main__":
    bg = make_background()
    frames = make_knob_strip()
    bypass_off = make_bypass()
    make_snapshot(bg, frames, bypass_off)
    print("done:", sorted(os.listdir(OUT)))
