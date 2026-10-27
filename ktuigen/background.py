# -*- coding: utf-8 -*-
"""Background rendering: base texture, panels, title logo, labels and knob scales."""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import gfx
from .gfx import rgba, lighten


# ---------------------------------------------------------------- textures (final resolution)
def _gradient(w, h, colors):
    colors = colors if isinstance(colors, list) else [colors]
    if len(colors) == 1:
        colors = colors * 2
    t = np.repeat((np.arange(h, dtype=np.float32) / max(1, h - 1))[:, None], w, axis=1)
    return gfx.ramp(t, [(i / (len(colors) - 1), c) for i, c in enumerate(colors)])


def _wood(w, h, colors, rng, s, vertical=False):
    if vertical:
        return np.transpose(_wood(h, w, colors, rng, s), (1, 0, 2))
    ys = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, axis=1)
    warp = gfx.smooth_noise(w, h, w / (90 * s) + 2, h / (30 * s) + 2, rng) * 2.2
    warp += gfx.smooth_noise(w, h, w / (300 * s) + 2, 3, rng) * 4.0
    g = np.sin(2 * math.pi * (ys / (7.0 * s) + warp))
    fiber = gfx.box_blur_x(rng.normal(0, 1, (h, w)).astype(np.float32), 25 * s) * 4.0
    v = np.clip(0.5 + 0.32 * g + 0.12 * fiber, 0, 1) ** 1.3
    light, dark = colors[0], colors[-1]
    return gfx.colorize(v, dark, light)


def _carbon(w, h, colors, s):
    cell = max(3, int(5 * s))
    ys, xs = np.mgrid[0:h, 0:w]
    ix, iy = (xs + ys) // cell, (xs - ys) // cell
    fx = ((xs + ys) % cell) / cell
    fy = ((xs - ys) % cell) / cell
    v = np.where((ix + iy) % 2 == 0, np.sin(np.pi * fx), np.sin(np.pi * fy)).astype(np.float32)
    return gfx.colorize(v * 0.8 + 0.1, colors[-1], lighten(colors[0], 0.1))


def base_texture(bg, w, h, s):
    rng = np.random.default_rng(int(bg.get("seed", 7)))
    style = bg.get("style", "brushed")
    colors = bg.get("colors") or ["#303338", "#17191d"]
    tex = float(bg.get("texture", 0.5))
    if style == "wood":
        col = _wood(w, h, colors, rng, s)
    elif style == "carbon":
        col = _carbon(w, h, colors, s)
    else:
        col = _gradient(w, h, colors if style != "solid" else [colors[0]])
    add = np.zeros((h, w), np.float32)
    if style == "brushed":
        r = int(45 * s)
        add += gfx.box_blur_x(rng.normal(0, 1, (h, w)).astype(np.float32), r) * math.sqrt(2 * r + 1) * 1.6 * tex
        add += rng.normal(0, 1, (h, 1)).astype(np.float32) * 1.4 * tex
        add += rng.normal(0, 1, (h, w)).astype(np.float32) * 1.2 * tex
    elif style in ("matte", "metallic", "grid"):
        add += rng.normal(0, 1, (h, w)).astype(np.float32) * 3.5 * tex
        add += gfx.smooth_noise(w, h, w / (60 * s) + 2, h / (60 * s) + 2, rng) * 4 * tex
        if style == "metallic":
            sp = rng.random((h, w)) < 0.035 * tex
            add += sp * rng.uniform(10, 45, (h, w)).astype(np.float32)
            add += gfx.smooth_noise(w, h, 4, 6, rng) * 7 * tex
    for i in range(3):
        col[..., i] += add
    v = float(bg.get("vignette", 0.0))
    if v:
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        d = ((xs / w - 0.5) * 2) ** 2 * 0.6 + ((ys / h - 0.42) * 2) ** 2
        col[..., :3] *= (1 - v * 0.35 * np.clip(d, 0, 2))[..., None]
    return col


# ---------------------------------------------------------------- vector drawing on the canvas
class Painter:
    def __init__(self, cfg, lay, scale):
        self.cfg, self.lay = cfg, lay
        self.W, self.H = lay["width"], lay["height"]
        self.ss = 3 if scale == 1 else 2
        self.u = scale * self.ss  # canvas px per logical px
        self.cw, self.ch = int(self.W * self.u), int(self.H * self.u)
        self.scale = scale

    def P(self, *v):
        return [x * self.u for x in v]

    def new(self, mode="RGBA"):
        return Image.new(mode, (self.cw, self.ch), 0 if mode == "L" else (0, 0, 0, 0))

    def text(self, img, xy, text, fspec, size, color, anchor="mt", spacing=0.0, effects=(), gradient=None,
             glow=None, outline=None):
        if not text:
            return img
        f = gfx.font(fspec, size * self.u)
        mask = self.new("L")
        gfx.draw_text(mask, (xy[0] * self.u, xy[1] * self.u), text, f, 255, anchor, spacing * size * self.u)
        return gfx.over(img, gfx.text_fx(mask, color, list(effects), self.u, gradient, glow, outline))


def render(cfg, lay, scale=1):
    bg, t = cfg["background"], cfg["title"]
    p = Painter(cfg, lay, scale)
    W, H, u = p.W, p.H, p.u
    fw, fh = W * scale, H * scale
    base = gfx.layer(base_texture(bg, fw, fh, scale))
    img = base.resize((p.cw, p.ch), Image.BICUBIC)

    radius = float(bg.get("corner_radius", 0)) * u
    shape = gfx.rounded_mask((p.cw, p.ch), [0, 0, p.cw - 1, p.ch - 1], radius)
    side = lay.get("side", 0)
    m = lay.get("margin", 16)

    if bg.get("style") == "grid":
        img = gfx.over(img, _grid(p, bg, lay))

    if side:
        rng = np.random.default_rng(int(bg.get("seed", 7)) + 1)
        wc = bg.get("wood_colors", ["#6b3e1f", "#3d2110"])
        for x0 in (0, W - side):
            wood = gfx.layer(_wood(int(side * scale), fh, wc, rng, scale, vertical=True))
            wood = wood.resize((int(side * u), p.ch), Image.BICUBIC)
            img.paste(wood, (int(x0 * u), 0))
        d = ImageDraw.Draw(img, "RGBA")  # blend, do not overwrite alpha
        for x in (side * u, (W - side) * u):
            d.line([(x - u, 0), (x - u, p.ch)], fill=(0, 0, 0, 160), width=int(u))
            d.line([(x, 0), (x, p.ch)], fill=(255, 255, 255, 30), width=int(u))

    # header separator
    hdr = lay.get("header")
    if hdr and bg.get("header_line"):
        d = ImageDraw.Draw(img, "RGBA")  # blend, do not overwrite alpha
        y = hdr["h"] * u
        x0, x1 = side * u, (W - side) * u
        d.line([(x0, y), (x1, y)], fill=(0, 0, 0, 150), width=int(u))
        d.line([(x0, y + u), (x1, y + u)], fill=(255, 255, 255, 34), width=int(u))

    # inset panel
    if lay.get("panel"):
        img = _panel(p, img, lay["panel"], bg)

    if bg.get("screws"):
        r = max(3.5, min(W, H) * 0.02)
        ins = max(r + 2, m * 0.45)
        for cx in (side + ins, W - side - ins):
            for cy in (ins, H - ins):
                img = gfx.over(img, _screw(p, cx, cy, r, bg.get("screw_color", "#a4a8b0"),
                                           (cx * 13 + cy * 7) % 180))

    # title block
    tb = lay.get("title")
    if tb:
        anchor = {"left": "l", "center": "m", "right": "r"}[tb["align"]]
        if t.get("accent_bar") and tb["align"] == "left" and t.get("text"):
            d = ImageDraw.Draw(img, "RGBA")  # blend, do not overwrite alpha
            d.rectangle(p.P(tb["x"] - 10, tb["y"] - 1, tb["x"] - 6, tb["y"] + tb["h"] + 1),
                        fill=rgba(t.get("accent_color")))
        img = p.text(img, (tb["x"], tb["y"]), t.get("text"), t["font"], tb["size"], t.get("color"),
                     anchor + "t", t.get("letter_spacing", 0), t.get("effects") or [], t.get("gradient"),
                     t.get("glow_color"), t.get("outline_color"))
        sub_fx = ["engrave"] if "engrave" in (t.get("effects") or []) else []
        img = p.text(img, (tb["x"], tb["sub_y"]), t.get("subtitle"), t["subtitle_font"], tb["sub_size"],
                     t.get("subtitle_color"), anchor + "t", t.get("subtitle_spacing", 0), sub_fx)

    # knob scales, labels
    lab = cfg["labels"]
    scale_layer = p.new()
    d = ImageDraw.Draw(scale_layer)
    for c in lay["controls"]:
        it = c["item"]
        if c["kind"] == "knobs":
            _ticks(d, p, c, it)
    img = gfx.over(img, scale_layer)
    for c in lay["controls"]:
        it = c["item"]
        if c["kind"] == "knobs" and it.get("range_labels"):
            s = c["w"]
            cx, cy = c["x"] + s / 2, c["y"] + s / 2
            rl = it["range_labels"]
            for ang, txt in ((it.get("start_angle", -135), rl[0]), (it.get("end_angle", 135), rl[-1])):
                x, y = gfx.angle_xy(cx, cy, s * 0.66, ang)
                img = p.text(img, (x, y + 2), str(txt), lab["font"], c["label"]["size"] * 0.78 if c["label"]
                             else 9, lab.get("dim_color"), "mm", 0.02)
        if c["kind"] == "toggles" and it.get("states"):
            img = _states(p, img, c, it, lab)
        if c["label"]:
            L = c["label"]
            y = L["y"]
            if lab.get("position") == "above" and c["kind"] != "leds":
                y = c["y"] - L["size"] * 1.4
            img = p.text(img, (L["x"], y), L["text"], lab["font"], L["size"], lab.get("color"), "mt",
                         lab.get("spacing", 0), lab.get("effects") or [])

    if bg.get("footer"):
        img = p.text(img, (W - m - side, H - 6), bg["footer"], lab["font"], 8.5, bg.get("footer_color"), "rb", 0.04)

    jk = lay.get("jacks")
    if jk:
        img = _jack_labels(p, img, jk, cfg)

    if bg.get("border", True):
        img = gfx.over(img, _border(p, radius))
    img.putalpha(shape)  # opaque body; only outside the rounded corners is transparent
    body = gfx.downsample(img, (int(W * scale), int(H * scale)))
    if not jk:
        return body
    # widen the canvas: jacks stick out of the enclosure sides (transparent around them)
    pl, pr = jk["pad_l"], jk["pad_r"]
    out = Image.new("RGBA", (int((W + pl + pr) * scale), int(H * scale)), (0, 0, 0, 0))
    out.paste(body, (int(pl * scale), 0))
    jack = render_jack(jk["h"], jk["p"], cfg["jacks"].get("metal_color", "#c9cdd3"), scale)
    for it in jk["items"]:
        y = int(round((it["cy"] - jk["h"] / 2) * scale))
        if it["side"] == "left":
            out.alpha_composite(jack, (0, y))
        else:
            out.alpha_composite(jack.transpose(Image.FLIP_LEFT_RIGHT), (int((pl + W) * scale), y))
    return out


def render_jack(h, p, metal, scale=1):
    """1/4" jack seen from the side, sticking out to the left (enclosure edge on the right).

    Threaded sleeve on the outside, hex nut against the enclosure wall."""
    S = gfx.SS
    w, hh = int(p * scale * S), int(h * scale * S)
    img = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    b = rgba(metal)
    ys = np.repeat((np.arange(hh, dtype=np.float32) / (hh - 1))[:, None], w, axis=1)
    # hex nut: three faces stacked vertically (top / front / bottom)
    nx0 = w * 0.48
    nut = gfx.ramp(ys, [(0.0, lighten(b, -0.35)), (0.24, lighten(b, -0.05)), (0.25, lighten(b, 0.35)),
                        (0.45, lighten(b, 0.6)), (0.75, lighten(b, -0.15)), (0.76, lighten(b, -0.5)),
                        (1.0, lighten(b, -0.7))])
    nm = gfx.rounded_mask((w, hh), [nx0, 0, w + hh, hh - 1], hh * 0.06)
    img = gfx.over(img, gfx.layer(nut, np.asarray(nm, np.float32) / 255))
    # strokes go on their own layer and are alpha-composited, so the jack stays fully opaque
    lines = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    d.line([(nx0, hh * 0.05), (nx0, hh * 0.95)], fill=lighten(b, 0.7)[:3] + (160,), width=max(1, S))
    img = gfx.over(img, lines)
    # threaded sleeve: chrome cylinder with thread grooves
    sy0, sy1 = hh * 0.2, hh * 0.8
    t = np.clip((ys - 0.2) / 0.6, 0, 1)
    sleeve = gfx.ramp(t, [(0.0, lighten(b, -0.6)), (0.25, lighten(b, 0.55)), (0.45, lighten(b, 0.1)),
                          (0.8, lighten(b, -0.35)), (1.0, lighten(b, -0.7))])
    sm = gfx.rounded_mask((w, hh), [0, sy0, nx0 + S, sy1], hh * 0.04)
    img = gfx.over(img, gfx.layer(sleeve, np.asarray(sm, np.float32) / 255))
    lines = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(lines)
    step = max(2 * S, min(hh * 0.075, nx0 / 3.5))
    x = step * 0.6
    while x < nx0 - step * 0.3:
        d.line([(x, sy0 + S), (x, sy1 - S)], fill=(0, 0, 0, 90), width=max(1, int(S * 0.9)))
        d.line([(x + S, sy0 + S), (x + S, sy1 - S)], fill=(255, 255, 255, 50), width=max(1, int(S * 0.7)))
        x += step
    # open end of the sleeve
    d.line([(S * 0.5, sy0 + S), (S * 0.5, sy1 - S)], fill=lighten(b, -0.6)[:3] + (200,), width=max(1, S))
    lines.putalpha(ImageChops.multiply(lines.getchannel("A"), sm))  # keep grooves inside the sleeve
    img = gfx.over(img, lines)
    out = gfx.downsample(img, (int(p * scale), int(h * scale)))
    out.putalpha(out.getchannel("A").point(lambda v: 0 if v < 16 else v))  # drop resampling ringing
    return out


def _jack_labels(p, img, jk, cfg):
    j, lab = cfg["jacks"], cfg["labels"]
    col = j.get("label_color") or lab.get("color")
    acol = rgba(j.get("arrow_color") or col)
    ls = jk["label_size"]
    cap = gfx.cap_height(gfx.font(lab["font"], ls))
    u = p.u
    for it in jk["items"]:
        x0, _, x1, _ = it["label_rect"]
        cy, aw, left = it["cy"], it["arrow_w"], it["side"] == "left"
        # arrow sits between the jack and the text
        if aw:
            ax0 = x0 if left else x1 - aw
            inward = it["dir"] == "in"
            right = inward if left else not inward  # points to +x?
            ah = cap * 0.5
            tip, base = (ax0 + aw, ax0) if right else (ax0, ax0 + aw)
            tri = [(base * u, (cy - ah) * u), (base * u, (cy + ah) * u), (tip * u, cy * u)]
            layer = p.new()
            ImageDraw.Draw(layer).polygon(tri, fill=acol)
            img = gfx.over(img, layer)
        if it["label"]:
            if left:
                img = p.text(img, (x1, cy), it["label"], lab["font"], ls, col, "rm", lab.get("spacing", 0))
            else:
                img = p.text(img, (x0, cy), it["label"], lab["font"], ls, col, "lm", lab.get("spacing", 0))
    return img


def _panel(p, img, box, bg):
    u = p.u
    r = float(bg.get("panel_radius", 10)) * u
    bx = p.P(*box)
    m = gfx.rounded_mask((p.cw, p.ch), bx, r)
    img = gfx.over(img, gfx.solid((p.cw, p.ch), bg.get("panel_color"), m))
    inner = gfx.shadow(m, 0, 2.5 * u, 2.5 * u, (0, 0, 0), 0.45)
    inv = ImageChops.invert(gfx.shift(m, 0, 2.5 * u))
    inner.putalpha(ImageChops.multiply(ImageChops.multiply(inner.getchannel("A"), m), inv.filter(
        ImageFilter.GaussianBlur(2 * u))))
    img = gfx.over(img, inner)
    d = ImageDraw.Draw(img, "RGBA")  # blend, do not overwrite alpha
    d.rounded_rectangle(bx, radius=r, outline=rgba(bg.get("panel_outline")), width=max(1, int(u)))
    return img


def _border(p, radius):
    u = p.u
    lay = p.new()
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, p.cw - 1, p.ch - 1], radius=radius, outline=(0, 0, 0, 200), width=int(u))
    hl = p.new()
    ImageDraw.Draw(hl).rounded_rectangle([u, u, p.cw - 1 - u, p.ch - 1 - u], radius=max(0, radius - u),
                                         outline=(255, 255, 255, 70), width=int(u))
    fade = np.repeat(np.clip(1.1 - np.linspace(0, 1, p.ch, dtype=np.float32) * 1.6, 0.05, 1)[:, None], p.cw, 1)
    hl.putalpha(ImageChops.multiply(hl.getchannel("A"), gfx.mask_from(fade)))
    return gfx.over(lay, hl)


def _screw(p, cx, cy, r, color, rot):
    u = p.u
    S = int((r * 3) * u)
    c = S / 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dx, dy, dist, _ = gfx.polar(S, S)
    R = r * u
    m = gfx.mask_from(gfx.disc(dist, R, 1.5))
    img = gfx.over(img, gfx.shadow(m, 0, 0.8 * u, 0.9 * u, (0, 0, 0), 0.7))
    t = np.clip(0.5 - (dx * 0.55 + dy * 0.83) / (2 * R), 0, 1)
    col = gfx.colorize(t, lighten(color, -0.55), lighten(color, 0.45))
    img = gfx.over(img, gfx.layer(col, gfx.disc(dist, R, 1.5)))
    d = ImageDraw.Draw(img, "RGBA")  # blend, do not overwrite alpha
    for a in (rot, rot + 90):
        x0, y0 = gfx.angle_xy(c, c, R * 0.62, a)
        x1, y1 = gfx.angle_xy(c, c, R * 0.62, a + 180)
        d.line([(x0 + u * 0.5, y0 + u * 0.5), (x1 + u * 0.5, y1 + u * 0.5)], fill=lighten(color, 0.5),
               width=max(1, int(R * 0.18)))
        d.line([(x0, y0), (x1, y1)], fill=lighten(color, -0.7), width=max(1, int(R * 0.22)))
    out = p.new()
    out.paste(img, (int(cx * u - c), int(cy * u - c)))
    return out


def _ticks(d, p, c, it):
    tk = it.get("ticks") or {}
    n = int(tk.get("count", 11) or 0)
    if n < 2:
        return
    u = p.u
    s = c["w"]
    cx, cy = (c["x"] + s / 2) * u, (c["y"] + s / 2) * u
    major = set(tk.get("major") or [])
    col = rgba(tk.get("color", "#a8acb4c8"))
    ln = float(tk.get("length", 1.0))
    a0, a1 = float(it.get("start_angle", -135)), float(it.get("end_angle", 135))
    r_in = s * 0.545 * u
    for i in range(n):
        a = a0 + (a1 - a0) * i / (n - 1)
        big = i in major
        if tk.get("style") == "dots":
            rr = (1.5 if big else 1.0) * u * max(0.8, s / 80)
            x, y = gfx.angle_xy(cx, cy, r_in + 2.5 * u, a)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
        else:
            r_out = r_in + s * (0.06 + (0.04 if big else 0)) * ln * u
            p0, p1 = gfx.angle_xy(cx, cy, r_in, a), gfx.angle_xy(cx, cy, r_out, a)
            d.line([p0, p1], fill=col, width=max(1, int(u * (1.4 if big else 1.1) * max(0.8, s / 80))))


def _states(p, img, c, it, lab):
    st = [str(s) for s in it["states"]]
    size = (c["label"]["size"] if c["label"] else 10) * 0.78
    cx, cy = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
    col = lab.get("dim_color")
    if it.get("axis") == "horizontal":
        img = p.text(img, (c["x"] - size * 0.5, cy), st[0], lab["font"], size, col, "rm", 0.05)
        img = p.text(img, (c["x"] + c["w"] + size * 0.5, cy), st[-1], lab["font"], size, col, "lm", 0.05)
    else:
        img = p.text(img, (cx, c["y"] - size * 0.5), st[-1], lab["font"], size, col, "mb", 0.05)
        img = p.text(img, (cx, c["y"] + c["h"] + size * 0.45), st[0], lab["font"], size, col, "mt", 0.05)
    if len(st) == 3:
        img = p.text(img, (c["x"] + c["w"] + size * 0.4, cy), st[1], lab["font"], size, col, "lm", 0.05)
    return img


def _grid(p, bg, lay):
    u = p.u
    W, H = p.W, p.H
    top = (lay["header"]["h"] if lay.get("header") else 0)
    hy = top + (H - top) * 0.38
    layer = p.new()
    d = ImageDraw.Draw(layer)
    col = rgba(bg.get("grid_color", "#ff4fd8"))
    tex = float(bg.get("texture", 0.5))
    n = 11
    for i in range(1, n + 1):
        f = (i / n) ** 2.2
        y = hy + (H - hy) * f
        a = int(255 * min(1, 0.15 + f) * 0.42 * tex)
        d.line([(0, y * u), (W * u, y * u)], fill=col[:3] + (a,), width=max(1, int(u * (0.8 + f))))
    vx = W / 2
    for k in range(-14, 15):
        x1 = vx + k * W / 9
        d.line([(vx * u, hy * u), (x1 * u, H * u)], fill=col[:3] + (int(95 * tex),), width=max(1, int(u)))
    fade = np.clip((np.arange(p.ch, dtype=np.float32) / u - hy) / (H - hy) * 1.6, 0, 1)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), gfx.mask_from(np.repeat(fade[:, None], p.cw, 1))))
    glow = layer.filter(ImageFilter.GaussianBlur(3 * u))
    hz = p.new()
    hd = ImageDraw.Draw(hz)
    hd.rectangle([0, (hy - 6) * u, W * u, (hy + 1) * u], fill=col[:3] + (int(70 * tex),))
    hz = hz.filter(ImageFilter.GaussianBlur(8 * u))
    return gfx.over(gfx.over(hz, glow), layer)
