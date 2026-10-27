# -*- coding: utf-8 -*-
"""Footswitches (button | stomp), toggle switches (bat | slide | pill) and LEDs (round | square)."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import gfx
from .gfx import SS, rgba, mix, lighten


def _blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _chrome(t, base="#d0d4da"):
    """Chrome-like ramp for a lighting value t 0..1."""
    b = rgba(base)
    return [(0.0, lighten(b, -0.72)), (0.35, lighten(b, -0.25)), (0.55, lighten(b, 0.15)),
            (0.7, lighten(b, -0.15)), (1.0, lighten(b, 0.75))]


def _lit(dx, dy, r):
    return np.clip(0.5 - (dx * 0.55 + dy * 0.83) / (2 * r), 0, 1)


def _hex(d, cx, cy, r, base, rot=0):
    """Hex nut with facet shading."""
    b = rgba(base)
    for i in range(6):
        a0 = math.radians(rot + 60 * i - 90)
        a1 = math.radians(rot + 60 * (i + 1) - 90)
        mid = (a0 + a1) / 2
        lv = 0.5 - 0.5 * (math.cos(mid) * 0.55 + math.sin(mid) * 0.83)
        col = mix(lighten(b, -0.55), lighten(b, 0.45), lv)
        d.polygon([(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                   (cx + r * math.cos(a1), cy + r * math.sin(a1))], fill=col)
    pts = [(cx + r * math.cos(math.radians(rot + 60 * i - 90)), cy + r * math.sin(math.radians(rot + 60 * i - 90)))
           for i in range(6)]
    d.polygon(pts, outline=lighten(b, -0.6), width=max(1, int(r * 0.03)))


def _radial_metal(w, h, cx, cy, r, base, inv=False, rings=0.0):
    dx, dy, dist, _ = gfx.polar(w, h, cx, cy)
    t = _lit(dx, dy, r)
    if inv:
        t = 1 - t
    if rings:
        t = np.clip(t + rings * np.sin(dist / (r * 0.07)), 0, 1)
    return gfx.layer(gfx.ramp(t, _chrome(t, base)), gfx.disc(dist, r, SS))


# ================================================================ footswitch
def render_footswitch(spec, w, h):
    style = spec.get("style", "button")
    frames = [_stomp(spec, w, on) if style == "stomp" else _button(spec, w, h, on) for on in (False, True)]
    return [gfx.downsample(f, (w, h)) for f in frames]


def _shade(v, base, lo=-0.75, hi=0.8):
    """Map a lighting value 0..1 to a metal tone around `base` -> (h,w,4)."""
    b = rgba(base)
    return gfx.ramp(v, [(0.0, lighten(b, lo)), (0.5, b), (1.0, lighten(b, hi))])


def _hex_dist(dx, dy, rot_deg):
    """Distance to the center measured along the nearest hexagon face normal (= inradius on the edge)."""
    d = np.zeros_like(dx)
    for k in range(3):
        a = math.radians(rot_deg + 60 * k)
        d = np.maximum(d, np.abs(dx * math.cos(a) + dy * math.sin(a)))
    return d


def _brushed(dist, r, seed, amount):
    """Concentric satin brushing: random brightness per radius ring."""
    rng = np.random.default_rng(seed)
    ring = rng.normal(0, 1, int(r * 1.2) + 8).astype(np.float32)
    ring = np.convolve(ring, np.ones(3, np.float32) / 3, "same")
    return ring[np.clip(dist.astype(int), 0, len(ring) - 1)] * amount


def _stomp(spec, size, on):
    """Photo-real 3PDT stomp switch seen from above:
    flat washer -> chamfered hex nut -> dark gap -> satin plunger cap (pressed: sunk, darker)."""
    S = size * SS
    c = S / 2
    aa = SS * 0.75
    metal = rgba(spec.get("metal_color", "#d0d4da"))
    washer_c = rgba(spec.get("washer_color") or lighten(metal, 0.05))
    dx, dy, dist, ang = gfx.polar(S, S)
    L = np.clip(-(dx * 0.55 + dy * 0.83) / np.maximum(dist, 1e-3), -1, 1)  # facing the top-left light
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    Rw = S * 0.43                     # washer (just beyond the nut corners)
    Rn_in = S * 0.335                 # hex nut inradius
    Rc = Rn_in * 0.93                 # chamfer circle (flat top of the nut)
    Rp = S * (0.205 if on else 0.218)  # plunger cap
    py = S * 0.006 if on else 0.0     # pressed cap sinks slightly
    Rh = Rp + S * 0.007               # thin outline hugging the cap

    # cast shadow of the whole switch onto the enclosure
    img = gfx.over(img, gfx.shadow(gfx.mask_from(gfx.disc(dist, Rw, aa)), 0, S * 0.03, S * 0.035,
                                   (0, 0, 0), 0.65))
    # washer: flat satin face, rounded outer edge
    edge = np.clip((dist - Rw * 0.9) / (Rw * 0.1), 0, 1)
    v = 0.5 + 0.1 * (-(dx * 0.55 + dy * 0.83) / Rw) + _brushed(dist, Rw, 11, 0.025)
    v = v * (1 - edge) + (0.42 + 0.45 * L) * edge
    img = gfx.over(img, gfx.layer(_shade(np.clip(v, 0, 1), washer_c, -0.6, 0.5), gfx.disc(dist, Rw, aa)))
    # nut casts a soft shadow on the washer
    hd = _hex_dist(dx, dy, 0)
    nut_a = np.clip((Rn_in - hd) / aa + 0.5, 0, 1)
    img = gfx.over(img, gfx.shadow(gfx.mask_from(nut_a), S * 0.012, S * 0.02, S * 0.018, (0, 0, 0), 0.55))
    # hex nut: chamfered corners lit by direction, flat satin top
    bevel = np.clip((dist - Rc) / (S * 0.006) + 0.5, 0, 1)
    top = 0.4 + 0.12 * (-(dx * 0.55 + dy * 0.83) / Rc) + 0.1 * np.cos(np.radians(ang + 45) * 2)         + _brushed(dist, Rc, 5, 0.035)
    side = 0.45 + 0.55 * L
    nv = top * (1 - bevel) + side * bevel
    img = gfx.over(img, gfx.layer(_shade(np.clip(nv, 0, 1), metal), nut_a))
    # thin dark line where the chamfer meets the top face
    ring = np.exp(-((dist - Rc) / (S * 0.004)) ** 2) * 0.3 * nut_a
    ring = np.maximum(ring, np.exp(-((hd - Rn_in) / (S * 0.004)) ** 2) * 0.45)  # nut outline
    ring = np.maximum(ring, np.exp(-((dist - Rw) / (S * 0.004)) ** 2) * 0.4 * (dist < Rw))  # washer edge
    img = gfx.over(img, gfx.layer(np.zeros(dist.shape + (4,), np.float32) + (0, 0, 0, 255), ring))
    # thin gray outline around the plunger (no real gap between cap and nut)
    od = np.hypot(dx, dy - py)
    gv = np.clip(0.45 + 0.2 * (-L), 0, 1)
    img = gfx.over(img, gfx.layer(_shade(gv, (128, 130, 135, 255), -0.5, 0.5), gfx.disc(od, Rh, aa)))

    # plunger cap
    cdx, cdy = dx, dy - py
    cd = np.hypot(cdx, cdy)
    CL = np.clip(-(cdx * 0.55 + cdy * 0.83) / np.maximum(cd, 1e-3), -1, 1)
    cap_a = gfx.disc(cd, Rp, aa)
    img = gfx.over(img, gfx.shadow(gfx.mask_from(cap_a), S * 0.01, S * (0.012 if on else 0.022),
                                   S * (0.01 if on else 0.016), (0, 0, 0), 0.85 if on else 0.7))
    rim = np.clip((cd - Rp * 0.84) / (Rp * 0.16), 0, 1)
    face = 0.56 + 0.16 * (-(cdx * 0.55 + cdy * 0.83) / Rp) + 0.08 * np.cos(np.radians(ang + 45) * 2)         + _brushed(cd, Rp, 3, 0.04)
    cv = face * (1 - rim) + (0.45 + 0.55 * CL) * rim
    if on:
        cv = cv * 0.75
    img = gfx.over(img, gfx.layer(_shade(np.clip(cv, 0, 1), metal), cap_a))
    # soft specular reflection on the cap face
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hx, hy = c - Rp * 0.3, c + py - Rp * 0.42
    ImageDraw.Draw(hl).ellipse([hx - Rp * 0.42, hy - Rp * 0.2, hx + Rp * 0.42, hy + Rp * 0.2],
                               fill=(255, 255, 255, 60 if on else 110))
    hl = hl.filter(ImageFilter.GaussianBlur(Rp * 0.14))
    hl.putalpha(gfx.ImageChops.multiply(hl.getchannel("A"), gfx.mask_from(cap_a * (1 - rim))))
    return gfx.over(img, hl)


def _button(spec, w, h, on):
    W, H = w * SS, h * SS
    img = _blank(W, H)
    u = H / 34.0
    r = 7 * u
    body = rgba(spec.get("on_color") if on else spec.get("color"))
    m = gfx.rounded_mask((W, H), [u, u, W - u, H - 1.5 * u], r)
    img = gfx.over(img, gfx.shadow(m, 0, u * 0.8, u * 1.0, (0, 0, 0), 0.6))
    dx, dy, _, _ = gfx.polar(W, H)
    t = np.clip(0.5 - dy / H, 0, 1)
    col = gfx.colorize(t, lighten(body, -0.18), lighten(body, 0.12 if not on else 0.06))
    img = gfx.over(img, gfx.layer(col, np.asarray(m, np.float32) / 255.0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([u, u, W - u, H - 1.5 * u], radius=r, outline=lighten(body, -0.55), width=max(1, int(u)))
    d.rounded_rectangle([2 * u, 2 * u, W - 2 * u, H - 2.5 * u], radius=r - u,
                        outline=lighten(body, 0.25 if gfx.luma(body) < 0.5 else -0.08), width=max(1, int(u)))
    text_x0 = 0
    if spec.get("led", True):
        lx, ly, lr = 15 * u, H / 2 - 0.25 * u, 4.6 * u
        led = _led_img(spec.get("led_color"), int(lr * 2 * 2.4), lr, 1.0 if on else 0.0, "none", "round")
        img = gfx.over(img, gfx.shift(_pad_to(led, W, H, lx - led.size[0] / 2, ly - led.size[1] / 2), 0, 0))
        text_x0 = 26 * u
    label = spec.get("text") or spec.get("label") or ""
    if label:
        f = gfx.font(spec.get("font") or "modern-label", 12.5 * u)
        sp = 0.06 * 12.5 * u
        tc = spec.get("text_color") if on else spec.get("text_dim")
        tw = gfx.text_width(label, f, sp)
        tx = text_x0 + (W - text_x0 - tw) / 2 - (2 * u if text_x0 else 0)
        mask = Image.new("L", (W, H), 0)
        gfx.draw_text(mask, (tx, H / 2 - 0.4 * u), label, f, 255, "lm", sp)
        img = gfx.over(img, gfx.text_fx(mask, tc, ["engrave"] if gfx.luma(body) > 0.6 else ["shadow"], u * 0.6))
    return img


def _pad_to(img, W, H, x, y):
    out = _blank(W, H)
    out.paste(img, (int(round(x)), int(round(y))), img)
    return out


# ================================================================ toggles
def render_toggle(spec, w, h):
    n = max(2, min(3, int(spec.get("positions", 2))))
    horiz = spec.get("axis") == "horizontal"
    style = spec.get("style", "bat")
    frames = []
    for i in range(n):
        t = i / (n - 1)
        if style == "pill":
            f = _pill(spec, w, h, t)
        else:
            rw, rh = (h, w) if horiz else (w, h)
            f = (_slide if style == "slide" else _bat)(spec, rw, rh, t)
            if horiz:
                f = f.rotate(-90, expand=True)
        frames.append(gfx.downsample(f, (w, h)))
    return frames


def _bat(spec, w, h, t):
    W, H = w * SS, h * SS
    cx, cy = W / 2, H / 2
    metal = spec.get("metal_color", "#c9cdd3")
    img = _blank(W, H)
    rn = W * 0.44
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([cx - rn, cy - rn, cx + rn, cy + rn], fill=255)
    img = gfx.over(img, gfx.shadow(m, 0, W * 0.05, W * 0.05, (0, 0, 0), 0.6))
    img = gfx.over(img, _radial_metal(W, H, cx, cy, rn * 1.0, lighten(metal, -0.1), rings=0.03))
    d = ImageDraw.Draw(img)
    _hex(d, cx, cy, rn * 0.86, metal, rot=30)
    rb = rn * 0.5
    img = gfx.over(img, _radial_metal(W, H, cx, cy, rb, lighten(metal, -0.3), inv=True))
    d = ImageDraw.Draw(img)
    d.ellipse([cx - rb * 0.55, cy - rb * 0.55, cx + rb * 0.55, cy + rb * 0.55], fill=(12, 12, 14, 255))

    # lever: t=0 down, 0.5 center, 1 up
    s = (t - 0.5) * 2  # -1..1 ; positive = up
    L = H * 0.40 * abs(s)
    tipr = W * 0.17
    lever = _blank(W, H)
    if abs(s) < 0.01:
        lever = gfx.over(lever, _radial_metal(W, H, cx, cy, tipr * 1.05, metal, rings=0.0))
    else:
        tip_y = cy - L if s > 0 else cy + L
        # cylinder shading across x
        xs = np.linspace(0, 1, W, dtype=np.float32)[None, :].repeat(H, 0)
        u = np.clip((xs * W - (cx - tipr)) / (2 * tipr), 0, 1)
        shade = gfx.ramp(1 - u, _chrome(None, metal))
        lm = Image.new("L", (W, H), 0)
        ld = ImageDraw.Draw(lm)
        bw, tw = W * 0.09, W * 0.13
        ld.polygon([(cx - bw, cy), (cx + bw, cy), (cx + tw, tip_y), (cx - tw, tip_y)], fill=255)
        ld.ellipse([cx - tipr, tip_y - tipr, cx + tipr, tip_y + tipr], fill=255)
        ld.ellipse([cx - bw, cy - bw, cx + bw, cy + bw], fill=255)
        sh = gfx.shadow(lm, W * 0.06, W * 0.10 if s > 0 else W * 0.03, W * 0.05, (0, 0, 0), 0.55)
        lever = gfx.over(lever, sh)
        lever = gfx.over(lever, gfx.layer(shade, np.asarray(lm, np.float32) / 255.0))
        tip = _radial_metal(W, H, cx, tip_y, tipr, metal, rings=0.0)
        lever = gfx.over(lever, tip)
        hl = _blank(W, H)
        ImageDraw.Draw(hl).ellipse([cx - tipr * 0.55, tip_y - tipr * 0.65, cx + tipr * 0.1, tip_y - tipr * 0.1],
                                   fill=(255, 255, 255, 150))
        lever = gfx.over(lever, hl.filter(ImageFilter.GaussianBlur(tipr * 0.15)))
    return gfx.over(img, lever)


def _slide(spec, w, h, t):
    W, H = w * SS, h * SS
    u = W / 20.0
    img = _blank(W, H)
    body = rgba(spec.get("body_color", "#1c1d21"))
    sx0, sx1 = W * 0.3, W * 0.7
    sy0, sy1 = H * 0.04, H * 0.96
    m = gfx.rounded_mask((W, H), [sx0, sy0, sx1, sy1], (sx1 - sx0) / 2)
    img = gfx.over(img, gfx.solid((W, H), lighten(body, -0.4), m))
    inner = gfx.shadow(m, 0, u * 1.2, u * 1.2, (0, 0, 0), 0.9)
    inner.putalpha(gfx.ImageChops.multiply(inner.getchannel("A"), m))
    img = gfx.over(img, inner)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=(sx1 - sx0) / 2, outline=lighten(body, 0.25), width=max(1, int(u * 0.4)))
    # thumb
    th = H * 0.36
    ty = sy0 + u + (1 - t) * (sy1 - sy0 - th - 2 * u)
    tx0, tx1 = W * 0.08, W * 0.92
    tm = gfx.rounded_mask((W, H), [tx0, ty, tx1, ty + th], u * 2.2)
    img = gfx.over(img, gfx.shadow(tm, 0, u * 1.2, u * 1.3, (0, 0, 0), 0.7))
    thumb = rgba(spec.get("thumb_color", "#e8eaee"))
    _, dy, _, _ = gfx.polar(W, H, W / 2, ty + th / 2)
    col = gfx.colorize(np.clip(0.5 - dy / th, 0, 1), lighten(thumb, -0.35), lighten(thumb, 0.2))
    img = gfx.over(img, gfx.layer(col, np.asarray(tm, np.float32) / 255.0))
    d = ImageDraw.Draw(img)
    for k in range(-2, 3):
        yy = ty + th / 2 + k * th * 0.14
        d.line([(tx0 + u * 2, yy), (tx1 - u * 2, yy)], fill=lighten(thumb, -0.45), width=max(1, int(u * 0.6)))
        d.line([(tx0 + u * 2, yy + u * 0.6), (tx1 - u * 2, yy + u * 0.6)], fill=lighten(thumb, 0.4),
               width=max(1, int(u * 0.4)))
    if t > 0.5:
        d.rounded_rectangle([tx0 + u * 2.5, ty + u * 1.2, tx1 - u * 2.5, ty + u * 2.2], radius=u * 0.5,
                            fill=rgba(spec.get("on_color")))
    return img


def _pill(spec, w, h, t):
    W, H = w * SS, h * SS
    img = _blank(W, H)
    r = H / 2 * 0.86
    box = [W / 2 - (W / 2 - (H / 2 - r)), H / 2 - r, W / 2 + (W / 2 - (H / 2 - r)), H / 2 + r]
    m = gfx.rounded_mask((W, H), box, r)
    on, off = rgba(spec.get("on_color")), rgba(spec.get("off_color"))
    col = mix(off, on, t)
    img = gfx.over(img, gfx.solid((W, H), col, m))
    inner = gfx.shadow(m, 0, H * 0.06, H * 0.06, (0, 0, 0), 0.35)
    inner.putalpha(gfx.ImageChops.multiply(inner.getchannel("A"), m))
    img = gfx.over(img, inner)
    kr = r * 0.82
    kx = box[0] + r + (box[2] - box[0] - 2 * r) * t
    km = Image.new("L", (W, H), 0)
    ImageDraw.Draw(km).ellipse([kx - kr, H / 2 - kr, kx + kr, H / 2 + kr], fill=255)
    img = gfx.over(img, gfx.shadow(km, 0, H * 0.04, H * 0.05, (0, 0, 0), 0.45))
    thumb = rgba(spec.get("thumb_color", "#ffffff"))
    _, dy, _, _ = gfx.polar(W, H, kx, H / 2)
    c = gfx.colorize(np.clip(0.5 - dy / (2 * kr), 0, 1), lighten(thumb, -0.1), thumb)
    return gfx.over(img, gfx.layer(c, np.asarray(km, np.float32) / 255.0))


# ================================================================ LEDs
def render_led(spec, w, h):
    n = max(2, int(spec.get("frames", 2)))
    S = w * SS
    lens = S / 2.4 / 2
    out = []
    for i in range(n):
        f = _led_img(spec.get("color"), S, lens, i / (n - 1), spec.get("bezel", "chrome"), spec.get("style", "round"))
        out.append(gfx.downsample(f, (w, h)))
    return out


def _led_img(color, S, r, t, bezel, shape):
    """S: canvas px (supersampled), r: lens radius px, t: brightness 0..1."""
    S = int(S)
    c = S / 2
    col = rgba(color)
    img = _blank(S, S)
    dx, dy, dist, _ = gfx.polar(S, S)
    if shape == "square":
        def mask(rr):
            return gfx.rounded_mask((S, S), [c - rr, c - rr, c + rr, c + rr], rr * 0.25)
    else:
        def mask(rr):
            return gfx.mask_from(gfx.disc(dist, rr, max(1, S / 120)))
    if bezel != "none":
        rb = r * 1.38
        if bezel == "chrome":
            img = gfx.over(img, gfx.shadow(mask(rb), 0, r * 0.15, r * 0.2, (0, 0, 0), 0.6))
            t_l = _lit(dx, dy, rb)
            img = gfx.over(img, gfx.layer(gfx.ramp(t_l, _chrome(t_l)), np.asarray(mask(rb), np.float32) / 255))
            img = gfx.over(img, gfx.solid((S, S), (10, 10, 12), mask(r * 1.1)))
        else:
            img = gfx.over(img, gfx.solid((S, S), (8, 8, 10), mask(rb)))
            img = gfx.over(img, gfx.shadow(mask(rb), 0, -r * 0.08, r * 0.05, (255, 255, 255), 0.12))
            img = gfx.over(img, gfx.solid((S, S), (8, 8, 10), mask(rb * 0.97)))
    else:
        img = gfx.over(img, gfx.shadow(mask(r * 1.05), 0, r * 0.12, r * 0.15, (0, 0, 0), 0.5))
    if t > 0:
        glow = gfx.solid((S, S), col[:3], mask(r * 1.25))
        a = glow.getchannel("A").filter(ImageFilter.GaussianBlur(r * 0.5)).point(lambda v: int(v * 0.85 * t))
        glow.putalpha(a)
        img = gfx.over(img, glow)
    off = mix(lighten(col, -0.78), lighten(col, -0.6), 0.5)
    hot = mix(col, (255, 255, 255, 255), 0.55)
    rd = np.clip(np.hypot(dx + r * 0.15, dy + r * 0.2) / r, 0, 1)
    c_off = gfx.colorize(rd, lighten(off, 0.25), lighten(off, -0.35))
    c_on = gfx.ramp(rd, [(0, hot), (0.55, col), (1, lighten(col, -0.25))])
    lens_col = c_off * (1 - t) + c_on * t
    img = gfx.over(img, gfx.layer(lens_col, np.asarray(mask(r), np.float32) / 255))
    spec_hl = _blank(S, S)
    ImageDraw.Draw(spec_hl).ellipse([c - r * 0.55, c - r * 0.7, c + r * 0.05, c - r * 0.2],
                                    fill=(255, 255, 255, int(110 + 80 * t)))
    img = gfx.over(img, spec_hl.filter(ImageFilter.GaussianBlur(r * 0.12)))
    return img
