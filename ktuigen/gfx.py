# -*- coding: utf-8 -*-
"""Low level drawing helpers: colors, numpy layers, shadows, fonts, text."""
import functools
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter, ImageFont

SS = 4  # supersampling factor for vector-ish parts


# ---------------------------------------------------------------- colors
def rgba(c, alpha=1.0):
    """Parse '#rgb', '#rrggbb', '#rrggbbaa', css names or [r,g,b(,a)] -> (r,g,b,a)."""
    if c is None:
        return (0, 0, 0, 0)
    if isinstance(c, str):
        v = ImageColor.getrgb(c)
    else:
        v = tuple(int(x) for x in c)
    if len(v) == 3:
        v = v + (255,)
    return v[:3] + (int(round(v[3] * alpha)),)


def mix(a, b, t):
    a, b = rgba(a), rgba(b)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))


def lighten(c, t):
    c = rgba(c)
    return mix(c, (255, 255, 255, c[3]), t) if t >= 0 else mix(c, (0, 0, 0, c[3]), -t)


def luma(c):
    c = rgba(c)
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0


# ---------------------------------------------------------------- numpy layers
def polar(w, h, cx=None, cy=None):
    """Return dx, dy, dist, angle(deg, screen coords: 0 = 3 o'clock, clockwise)."""
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
    return dx, dy, np.hypot(dx, dy), np.degrees(np.arctan2(dy, dx))


def disc(dist, r, soft=1.0):
    """Anti-aliased disc coverage 0..1."""
    return np.clip((r - dist) / soft + 0.5, 0.0, 1.0)


def ramp(t, stops):
    """Piecewise-linear color ramp. t: array 0..1, stops: [(pos, color), ...] -> (h,w,4) float."""
    t = np.clip(t, 0.0, 1.0)
    pos = np.array([p for p, _ in stops], np.float32)
    cols = np.array([rgba(c) for _, c in stops], np.float32)
    out = np.empty(t.shape + (4,), np.float32)
    for ch in range(4):
        out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out


def colorize(t, c0, c1):
    return ramp(t, [(0.0, c0), (1.0, c1)])


def layer(rgb, alpha=None):
    """rgb: (h,w,3|4) float 0..255, alpha: (h,w) 0..1 multiplies -> RGBA Image."""
    a = rgb[..., 3] / 255.0 if rgb.shape[-1] == 4 else np.ones(rgb.shape[:2], np.float32)
    if alpha is not None:
        a = a * alpha
    out = np.empty(rgb.shape[:2] + (4,), np.uint8)
    out[..., :3] = np.clip(rgb[..., :3], 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def solid(size, color, mask=None):
    img = Image.new("RGBA", size, rgba(color))
    if mask is not None:
        a = ImageChops.multiply(img.getchannel("A"), mask)
        img.putalpha(a)
    return img


def mask_from(arr):
    return Image.fromarray(np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8), "L")


def shift(img, dx, dy):
    out = Image.new(img.mode, img.size, 0)
    out.paste(img, (int(round(dx)), int(round(dy))))
    return out


def shadow(mask, dx, dy, blur, color=(0, 0, 0), opacity=0.6):
    """mask: L image. returns RGBA blurred shadow."""
    m = shift(mask, dx, dy)
    if blur > 0:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    if opacity != 1.0:
        m = m.point(lambda v: int(v * opacity))
    return solid(mask.size, rgba(color)[:3], m)


def over(dst, src):
    return Image.alpha_composite(dst, src)


def downsample(img, size):
    return img.resize(size, Image.LANCZOS)


def strip(frames, orientation):
    """Concatenate equal sized frames vertically or horizontally."""
    w, h = frames[0].size
    if orientation == "horizontal":
        out = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            out.paste(f, (i * w, 0))
    else:
        out = Image.new("RGBA", (w, h * len(frames)), (0, 0, 0, 0))
        for i, f in enumerate(frames):
            out.paste(f, (0, i * h))
    return out


def box_blur_x(a, r):
    """Fast horizontal box blur of a 2D array with radius r (pixels)."""
    r = max(1, int(r))
    p = np.pad(a, ((0, 0), (r + 1, r)), mode="edge")
    c = np.cumsum(p, axis=1, dtype=np.float64)
    return ((c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)).astype(np.float32)


def smooth_noise(w, h, cells_x, cells_y, rng):
    """Low frequency value noise (h,w) in -1..1 by bicubic upscaling of random grid."""
    g = rng.uniform(0, 255, (max(2, int(cells_y)), max(2, int(cells_x)))).astype(np.uint8)
    im = Image.fromarray(g, "L").resize((w, h), Image.BICUBIC)
    return np.asarray(im, np.float32) / 127.5 - 1.0


# ---------------------------------------------------------------- fonts
FONT_ALIASES = {
    "sans": ["segoeui.ttf", "arial.ttf", "Helvetica.ttc", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    "sans-bold": ["segoeuib.ttf", "arialbd.ttf", "Helvetica.ttc", "DejaVuSans-Bold.ttf",
                  "LiberationSans-Bold.ttf"],
    "modern": ["bahnschrift.ttf:Bold", "segoeuib.ttf", "Avenir Next Condensed.ttc", "DejaVuSansCondensed-Bold.ttf"],
    "modern-label": ["bahnschrift.ttf:SemiBold", "segoeuib.ttf", "Avenir Next.ttc", "DejaVuSans-Bold.ttf"],
    "condensed": ["bahnschrift.ttf:Bold Condensed", "ARIALNB.TTF", "DejaVuSansCondensed-Bold.ttf"],
    "heavy": ["ariblk.ttf", "Arial Black.ttf", "impact.ttf", "DejaVuSans-Bold.ttf"],
    "impact": ["impact.ttf", "Impact.ttf", "ariblk.ttf", "DejaVuSans-Bold.ttf"],
    "serif": ["georgia.ttf", "times.ttf", "Georgia.ttf", "DejaVuSerif.ttf"],
    "serif-bold": ["palabi.ttf", "georgiaz.ttf", "Georgia Bold Italic.ttf", "DejaVuSerif-BoldItalic.ttf"],
    "serif-label": ["georgiab.ttf", "timesbd.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"],
    "mono": ["consolab.ttf", "courbd.ttf", "Menlo.ttc", "DejaVuSansMono-Bold.ttf"],
}


def _font_dirs():
    dirs = []
    if sys.platform == "win32":
        dirs.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
        la = os.environ.get("LOCALAPPDATA")
        if la:
            dirs.append(os.path.join(la, "Microsoft", "Windows", "Fonts"))
    elif sys.platform == "darwin":
        dirs += ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
                 os.path.expanduser("~/Library/Fonts")]
    else:
        dirs += ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
                 os.path.expanduser("~/.local/share/fonts")]
    return [d for d in dirs if os.path.isdir(d)]


@functools.lru_cache(maxsize=1)
def _font_index():
    idx = {}
    for d in _font_dirs():
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith((".ttf", ".otf", ".ttc")):
                    idx.setdefault(f.lower(), os.path.join(root, f))
    return idx


def _split_variation(spec):
    left, sep, right = spec.rpartition(":")
    if sep and left and len(left) > 1 and "/" not in right and "\\" not in right:
        return left, right
    return spec, None


def _resolve_font_path(name):
    if os.path.isfile(name):
        return name
    idx = _font_index()
    key = name.lower()
    for k in (key, key + ".ttf", key + ".otf", key + ".ttc"):
        if k in idx:
            return idx[k]
    return None


@functools.lru_cache(maxsize=256)
def _load_font(spec_t, size):
    specs = []
    for s in spec_t:
        specs += FONT_ALIASES.get(s, [s])
    specs += FONT_ALIASES["sans-bold"]
    for s in specs:
        name, var = _split_variation(s)
        path = _resolve_font_path(name)
        if not path:
            continue
        try:
            f = ImageFont.truetype(path, size)
        except OSError:
            continue
        if var:
            try:
                f.set_variation_by_name(var)
            except Exception:
                pass
        return f
    return ImageFont.load_default(size)


def font(spec, size):
    if isinstance(spec, str):
        spec = [spec]
    return _load_font(tuple(spec or ["sans-bold"]), max(1, int(round(size))))


# ---------------------------------------------------------------- text
def text_width(text, f, spacing=0.0):
    if not text:
        return 0.0
    if not spacing:
        return f.getlength(text)
    return sum(f.getlength(ch) for ch in text) + spacing * (len(text) - 1)


def cap_height(f):
    b = f.getbbox("H", anchor="ls")
    return -b[1]


def draw_text(img, xy, text, f, fill=255, anchor="lt", spacing=0.0):
    """Draw text with letter spacing. anchor: [l|m|r][t|m|b|s], vertical measured on cap height."""
    if not text:
        return
    d = ImageDraw.Draw(img)
    x, y = xy
    w = text_width(text, f, spacing)
    h = cap_height(f)
    x -= {"l": 0, "m": w / 2, "r": w}[anchor[0]]
    base = y + {"t": h, "m": h / 2, "b": 0, "s": 0}[anchor[1]]
    if not spacing:
        d.text((x, base), text, font=f, fill=fill, anchor="ls")
        return
    for ch in text:
        d.text((x, base), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + spacing


def text_fx(mask, fill, effects, unit, gradient=None, glow_color=None, outline_color=None):
    """Render a text mask (L) into an RGBA layer with logo-ish effects.

    effects: list of 'shadow' | 'emboss' | 'engrave' | 'glow' | 'outline' | 'bevel'
    unit: pixel size of 1 logical px (scale * supersampling) used for offsets.
    """
    size = mask.size
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    fx = set(effects or [])
    u = unit
    fill_c = rgba(fill)

    if "glow" in fx:
        gc = rgba(glow_color or fill)
        for blur, op in ((10 * u, 0.55), (4 * u, 0.7)):
            out = over(out, shadow(mask, 0, 0, blur, gc[:3], op))
    if "shadow" in fx:
        out = over(out, shadow(mask, 0, 1.6 * u, 2.2 * u, (0, 0, 0), 0.75))
    if "outline" in fx:
        k = max(3, int(2.4 * u) | 1)
        dil = mask.filter(ImageFilter.MaxFilter(k))
        out = over(out, solid(size, outline_color or (0, 0, 0), dil))
    if "emboss" in fx:
        out = over(out, shadow(mask, -0.8 * u, -0.8 * u, 0.4 * u, (255, 255, 255), 0.25))
        out = over(out, shadow(mask, 0.9 * u, 1.2 * u, 0.6 * u, (0, 0, 0), 0.7))
    if "engrave" in fx:
        out = over(out, shadow(mask, 0, 1.0 * u, 0.3 * u, (255, 255, 255), 0.30))

    if gradient:
        bb = mask.getbbox() or (0, 0, size[0], size[1])
        h = max(1, bb[3] - bb[1])
        t = np.clip((np.arange(size[1], dtype=np.float32) - bb[1]) / h, 0, 1)
        stops = [(i / (len(gradient) - 1), c) for i, c in enumerate(gradient)]
        col = ramp(np.repeat(t[:, None], size[0], axis=1), stops)
        body = layer(col, np.asarray(mask, np.float32) / 255.0)
    else:
        body = solid(size, fill_c, mask)
    out = over(out, body)

    if "bevel" in fx:
        hi = ImageChops.subtract(mask, shift(mask, 0, 1.0 * u)).filter(ImageFilter.GaussianBlur(0.4 * u))
        out = over(out, solid(size, (255, 255, 255), hi.point(lambda v: int(v * 0.55))))
    if "engrave" in fx:
        inner = ImageChops.subtract(mask, shift(mask, 0, 1.2 * u)).filter(ImageFilter.GaussianBlur(0.5 * u))
        out = over(out, solid(size, (0, 0, 0), inner.point(lambda v: int(v * 0.6))))
    return out


def rounded_mask(size, box, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=max(0, radius), fill=255)
    return m


def angle_xy(cx, cy, r, deg_from_top):
    """Point on circle. deg_from_top: 0 = 12 o'clock, clockwise."""
    a = math.radians(deg_from_top - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)
