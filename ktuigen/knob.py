# -*- coding: utf-8 -*-
"""Rotary knob film strips. Styles: modern | pedal | vintage | flat | metal."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import gfx
from .gfx import SS, rgba, mix, lighten


def _lit(dx, dy, r):
    """Directional light from the top-left: 0 (dark side) .. 1 (lit side)."""
    return np.clip(0.5 - (dx * 0.55 + dy * 0.83) / (2 * r), 0, 1)


def _knurl(ang, rot, n):
    """Ridge shading -1..1 for n ridges rotated by rot degrees."""
    return np.cos(np.radians(ang - rot) * n)


class Knob:
    def __init__(self, spec, px):
        self.p = spec
        self.px = px
        self.S = px * SS
        self.c = self.S / 2
        self.dx, self.dy, self.dist, self.ang = gfx.polar(self.S, self.S)
        arc = spec.get("arc")
        self.R = self.S * (0.355 if arc else 0.43)
        self.ra = self.S * 0.455
        self.aw = self.S * 0.042 * float(spec.get("arc_width", 1.0))
        self.style = spec.get("style", "modern")
        self._static = {}

    # -------------------------------------------------- common layers
    def blank(self):
        return Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))

    def shadow_layer(self, r_scale=1.0):
        op = float(self.p.get("shadow", 0.6))
        m = gfx.mask_from(gfx.disc(self.dist, self.R * r_scale, SS))
        return gfx.shadow(m, 0, self.S * 0.035, self.S * 0.035, (0, 0, 0), op)

    def angle(self, t):
        a0, a1 = float(self.p.get("start_angle", -135)), float(self.p.get("end_angle", 135))
        return a0 + (a1 - a0) * t

    def arc_layer(self, t):
        img = self.blank()
        d = ImageDraw.Draw(img)
        c, r = self.c, self.ra
        box = [c - r, c - r, c + r, c + r]
        a0, a1 = self.angle(0) - 90, self.angle(1) - 90
        w = max(1, int(self.aw))
        d.arc(box, a0, a1, fill=rgba(self.p.get("arc_track_color")), width=w)
        start = self.angle(0.5) if self.p.get("bipolar") else self.angle(0)
        end = self.angle(t)
        lo, hi = sorted((start, end))
        if hi - lo > 0.4:
            lit = self.blank()
            ImageDraw.Draw(lit).arc(box, lo - 90, hi - 90, fill=rgba(self.p.get("arc_color")), width=w)
            if self.p.get("arc_glow"):
                g = lit.filter(ImageFilter.GaussianBlur(self.aw * 1.2))
                img = gfx.over(img, g)
                img = gfx.over(img, g)
            img = gfx.over(img, lit)
        return img

    def pointer_layer(self, t, r0, r1, width, color, outline=True, tip=None):
        img = self.blank()
        d = ImageDraw.Draw(img)
        a = self.angle(t)
        p0 = gfx.angle_xy(self.c, self.c, r0, a)
        p1 = gfx.angle_xy(self.c, self.c, r1, a)
        kind = self.p.get("pointer", "line")
        if kind == "none":
            return img
        if kind == "dot":
            rr = width * 0.9
            cx, cy = gfx.angle_xy(self.c, self.c, (r0 + r1) / 2 + (r1 - r0) * 0.25, a)
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=rgba(color))
            return img
        if outline:
            d.line([p0, p1], fill=(0, 0, 0, 150), width=int(width * 1.8))
            for p in (p0, p1):
                rr = width * 0.9
                d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=(0, 0, 0, 150))
        d.line([p0, p1], fill=rgba(color), width=int(width))
        for p in (p0, p1):
            rr = width / 2
            d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=rgba(color))
        if tip:
            rr = width * 0.62
            d.ellipse([p1[0] - rr, p1[1] - rr, p1[0] + rr, p1[1] + rr], fill=rgba(tip))
        return img

    def highlight_layer(self, cx_off, cy_off, rx, ry, alpha):
        alpha *= float(self.p.get("highlight", 1.0))
        img = self.blank()
        if alpha <= 0:
            return img
        d = ImageDraw.Draw(img)
        cx, cy = self.c + cx_off * self.R, self.c + cy_off * self.R
        d.ellipse([cx - rx * self.R, cy - ry * self.R, cx + rx * self.R, cy + ry * self.R],
                  fill=(255, 255, 255, int(255 * alpha)))
        return img.filter(ImageFilter.GaussianBlur(self.R * 0.12))

    def clip(self, img, r):
        a = np.asarray(img.getchannel("A"), np.float32) / 255.0 * gfx.disc(self.dist, r, SS)
        img.putalpha(gfx.mask_from(a))
        return img

    # -------------------------------------------------- styles
    def body_modern(self):
        R, p = self.R, self.p
        dx, dy, dist = self.dx, self.dy, self.dist
        lit = _lit(dx, dy, R)
        edge = rgba(p.get("edge_color"))
        bezel = gfx.ramp(lit, [(0, edge), (0.6, lighten(edge, 0.12)), (1, lighten(edge, 0.45))])
        img = gfx.layer(bezel, gfx.disc(dist, R, SS))
        inner = R * 0.9
        rd = np.hypot(dx + inner * 0.42, dy + inner * 0.55) / (2.0 * inner)
        col = gfx.colorize(1 - np.clip(rd, 0, 1), p.get("body_color"), p.get("body_color2"))
        e = np.clip((dist / inner - 0.84) / 0.16, 0, 1)[..., None]
        col = col * (1 - e * 0.55)
        img = gfx.over(img, gfx.layer(col, gfx.disc(dist, inner, SS)))
        return img

    def body_flat(self):
        R, p = self.R, self.p
        img = gfx.layer(np.broadcast_to(np.array(rgba(p.get("edge_color")), np.float32),
                                        self.dist.shape + (4,)).copy(), gfx.disc(self.dist, R, SS))
        t = np.clip((self.dy / R + 1) / 2, 0, 1)
        col = gfx.colorize(t, p.get("body_color"), p.get("body_color2"))
        return gfx.over(img, gfx.layer(col, gfx.disc(self.dist, R - 1.2 * SS * self.px / 80, SS)))

    def body_metal(self):
        R, p = self.R, self.p
        dist, ang = self.dist, self.ang
        rng = np.random.default_rng(3)
        # concentric brushing: random brightness per radius
        ring = rng.normal(0, 1, int(R) + 4).astype(np.float32)
        ring = np.convolve(ring, np.ones(3) / 3, "same")
        brush = ring[np.clip(dist.astype(int), 0, len(ring) - 1)] * 6
        base = rgba(p.get("body_color2") if p.get("body_color2") else "#c8ccd2")
        refl = 0.62 + 0.24 * np.cos(np.radians(ang + 45) * 2) + 0.08 * np.cos(np.radians(ang + 45) * 4)
        col = np.empty(dist.shape + (4,), np.float32)
        for i in range(3):
            col[..., i] = base[i] * refl + brush
        col[..., 3] = 255
        edge = _lit(self.dx, self.dy, R)
        bev = gfx.ramp(edge, [(0, "#2a2c30"), (0.5, "#6a6e76"), (1, "#f2f4f8")])
        img = gfx.layer(bev, gfx.disc(dist, R, SS))
        return gfx.over(img, gfx.layer(col, gfx.disc(dist, R * 0.93, SS)))

    def skirt_knurled(self, rot, n, r_out, r_in, c0, c1, depth=0.035):
        """Knurled grip ring with scalloped silhouette, rotating with the knob."""
        ridge = _knurl(self.ang, rot, n)
        r_edge = r_out * (1 - depth * (0.5 - 0.5 * ridge))
        lit = _lit(self.dx, self.dy, r_out)
        # ridge flanks catch the light depending on their orientation
        flank = np.sin(np.radians(self.ang - rot) * n) * np.sin(np.radians(self.ang + 135))
        v = np.clip(lit * 0.55 + 0.25 + 0.22 * flank + 0.08 * ridge, 0, 1)
        col = gfx.colorize(v, c0, c1)
        a = gfx.disc(self.dist, r_edge, SS) * (1 - gfx.disc(self.dist, r_in, SS) * 0)
        return gfx.layer(col, a)

    # -------------------------------------------------- frames
    def frame(self, t):
        st, p, R, S = self.style, self.p, self.R, self.S
        rot = self.angle(t)
        if "under" not in self._static:
            self._static["under"] = self.shadow_layer(1.02)
        img = self._static["under"].copy()
        if p.get("arc"):
            img = gfx.over(img, self.arc_layer(t))
        if st == "modern":
            if "body" not in self._static:
                self._static["body"] = self.body_modern()
                self._static["hl"] = self.highlight_layer(-0.2, -0.45, 0.62, 0.36, 0.13)
            img = gfx.over(img, self._static["body"])
            img = gfx.over(img, self.pointer_layer(t, R * 0.32, R * 0.78, R * 0.085, p["pointer_color"],
                                                   tip=p.get("pointer_tip")))
            img = gfx.over(img, self._static["hl"])
        elif st == "flat":
            if "body" not in self._static:
                self._static["body"] = self.body_flat()
            img = gfx.over(img, self._static["body"])
            img = gfx.over(img, self.pointer_layer(t, R * 0.35, R * 0.8, R * 0.11, p["pointer_color"],
                                                   outline=False))
        elif st == "metal":
            if "body" not in self._static:
                self._static["body"] = self.body_metal()
                self._static["hl"] = self.highlight_layer(-0.15, -0.5, 0.5, 0.25, 0.10)
            img = gfx.over(img, self._static["body"])
            groove = self.pointer_layer(t, R * 0.22, R * 0.86, R * 0.075, p["pointer_color"], outline=False)
            light = self.pointer_layer(t, R * 0.22, R * 0.86, R * 0.075, (255, 255, 255, 110), outline=False)
            img = gfx.over(img, gfx.shift(light, 0, max(1, R * 0.03)))
            img = gfx.over(img, groove)
            img = gfx.over(img, self._static["hl"])
        elif st == "pedal":
            n = int(p.get("ridges") or 28)
            body = rgba(p.get("body_color"))
            img = gfx.over(img, self.skirt_knurled(rot, n, R, R * 0.7, body, p.get("body_color2")))
            if "cap" not in self._static:
                rc = R * 0.74
                ring = gfx.layer(gfx.ramp(_lit(self.dx, self.dy, rc),
                                          [(0, lighten(body, -0.4)), (1, lighten(body, 0.25))]),
                                 gfx.disc(self.dist, rc, SS))
                sheen = 0.5 + 0.12 * np.cos(np.radians(self.ang + 45) * 2)
                capc = gfx.colorize(sheen, lighten(p.get("cap_color"), -0.2), lighten(p.get("cap_color"), 0.25))
                cap = gfx.layer(capc, gfx.disc(self.dist, rc * 0.93, SS))
                self._static["cap"] = gfx.over(ring, cap)
                self._static["hl"] = self.highlight_layer(-0.2, -0.42, 0.5, 0.3, 0.12)
            img = gfx.over(img, self._static["cap"])
            img = gfx.over(img, self.pointer_layer(t, R * 0.12, R * 0.97, R * 0.09, p["pointer_color"],
                                                   outline=False))
            img = gfx.over(img, self._static["hl"])
        elif st == "vintage":
            n = int(p.get("ridges") or 36)
            body = rgba(p.get("body_color"))
            img = gfx.over(img, self.skirt_knurled(rot, n, R, R * 0.6, lighten(body, -0.35),
                                                   p.get("body_color2"), depth=0.02))
            if "cap" not in self._static:
                rf = R * 0.8
                face = gfx.layer(gfx.ramp(_lit(self.dx, self.dy, rf),
                                          [(0, lighten(body, -0.2)), (0.6, body), (1, p.get("body_color2"))]),
                                 gfx.disc(self.dist, rf, SS))
                rc = R * 0.5
                capc = rgba(p.get("cap_color"))
                rd = np.hypot(self.dx + rc * 0.4, self.dy + rc * 0.5) / (2 * rc)
                ringv = 0.06 * np.sin(self.dist / (rc * 0.09))
                cap = gfx.colorize(np.clip(1 - rd + ringv, 0, 1), lighten(capc, -0.45), lighten(capc, 0.5))
                capl = gfx.layer(cap, gfx.disc(self.dist, rc, SS))
                rim = gfx.shadow(gfx.mask_from(gfx.disc(self.dist, rc, SS)), 0, R * 0.03, R * 0.04, (0, 0, 0), 0.5)
                self._static["cap"] = gfx.over(gfx.over(face, rim), capl)
                self._static["hl"] = self.highlight_layer(-0.25, -0.45, 0.5, 0.28, 0.16)
            img = gfx.over(img, self._static["cap"])
            img = gfx.over(img, self.pointer_layer(t, R * 0.56, R * 0.96, R * 0.07, p["pointer_color"],
                                                   outline=False))
            img = gfx.over(img, self._static["hl"])
        else:
            raise ValueError(f"unknown knob style {st!r}")
        return gfx.downsample(img, (self.px, self.px))


def render(spec, px):
    """Returns list of frames (RGBA px x px)."""
    k = Knob(spec, px)
    n = max(2, int(spec.get("frames", 101)))
    return [k.frame(i / (n - 1)) for i in range(n)]
