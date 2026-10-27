# -*- coding: utf-8 -*-
"""Automatic layout. All coordinates are logical pixels (before `scale`)."""
import math

from . import gfx


def _even(v):
    return max(2, int(round(v / 2.0)) * 2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------- part sizes
def part_size(kind, it, k, where="main", header_h=0):
    """Image size (w, h) of a control for a base knob size k."""
    rel = float(it.get("rel") or 1.0)
    size = it.get("size")
    if kind == "knobs":
        s = _even(size or k * rel)
        return s, s
    if kind == "toggles":
        style = it.get("style", "bat")
        S = size or k * rel * (0.62 if style == "pill" else 0.74)
        if style == "pill":
            w, h = _even(S), _even(S * 0.52)
        elif style == "slide":
            w, h = _even(S * 0.42), _even(S)
        else:
            w, h = _even(S * 0.6), _even(S)
        return (h, w) if it.get("axis") == "horizontal" and style != "pill" else (w, h)
    if kind == "footswitches":
        if it.get("style") == "stomp":
            s = _even(size or k * rel * 0.82)
            return s, s
        if where == "header":
            h = _even(clamp(header_h * 0.46, 22, 40))
            w = _even(size or h * 2.8)
            return w, _even(w / 2.8) if size else h
        w = _even(size or k * rel * 1.15)
        return w, _even(w / 2.8)
    if kind == "leds":
        d = size or clamp(k * 0.16, 8, 16)
        return _even(d * 2.4), _even(d * 2.4)
    raise ValueError(kind)


def led_lens(w):
    return w / 2.4


# ---------------------------------------------------------------- helpers
class Ctx:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lab = cfg["labels"]

    def label_size(self, k):
        return int(self.lab.get("size") or round(clamp(k * 0.15, 9, 15)))

    def label_w(self, text, ls):
        f = gfx.font(self.lab["font"], ls)
        return gfx.text_width(text, f, self.lab.get("spacing", 0) * ls)


def _cell(ctx, kind, it, k, ls, where="main", header_h=0, tight=False):
    pw, ph = part_size(kind, it, k, where, header_h)
    label = it.get("label") or ""
    if kind == "footswitches" and it.get("style") != "stomp":
        label = ""  # button carries its text inside
    lw = ctx.label_w(label, ls) + ls * 1.2 if label else 0
    if kind == "knobs":
        area = pw * 1.24
        cw = pw * (1.3 if tight else 1.42)
        if it.get("range_labels"):
            cw = pw * 1.62
    elif kind == "toggles":
        states = it.get("states")
        area = ph + (ls * 2.4 if states and it.get("axis") != "horizontal" else 0)
        cw = max(pw * 2.0, k * 0.7)
        if states and it.get("axis") == "horizontal":
            cw = pw + 2 * max(ctx.label_w(str(s), int(ls * 0.85)) for s in states) + ls * 2
    elif kind == "leds":
        area = ph
        cw = pw * 1.3
    else:
        area = ph
        cw = pw * 1.3
    return {"kind": kind, "item": it, "w": pw, "h": ph, "cell_w": max(cw, lw), "area": area,
            "label": label}


def _label_h(ls):
    return ls * 1.9


def _wrap(cells, avail_w, max_rows):
    rows, cur, cw = [], [], 0
    for c in cells:
        if cur and cw + c["cell_w"] > avail_w:
            rows.append(cur)
            cur, cw = [], 0
        cur.append(c)
        cw += c["cell_w"]
    if cur:
        rows.append(cur)
    if len(rows) > max_rows or any(sum(c["cell_w"] for c in r) > avail_w for r in rows):
        return None
    return rows


def _row_h(row, ls):
    area = max(c["area"] for c in row)
    lab = _label_h(ls) if any(c["label"] for c in row) else 0
    return area, area + lab


def _place_row(row, x0, avail_w, y, ls, out):
    area, _ = _row_h(row, ls)
    total = sum(c["cell_w"] for c in row)
    gap = (avail_w - total) / (len(row) + 1)
    gap = min(gap, max(c["cell_w"] for c in row) * 0.6) if len(row) > 1 else gap
    x = x0 + (avail_w - total - gap * (len(row) - 1)) / 2
    cy = y + area / 2
    for c in row:
        cx = x + c["cell_w"] / 2
        _emit(c, cx, cy, y + area + ls * 0.45, ls, out)
        x += c["cell_w"] + gap


def _emit(c, cx, cy, label_top, ls, out):
    ctl = {
        "kind": c["kind"], "item": c["item"],
        "x": int(round(cx - c["w"] / 2)), "y": int(round(cy - c["h"] / 2)), "w": c["w"], "h": c["h"],
        "label": {"text": c["label"], "x": cx, "y": label_top, "size": ls} if c["label"] else None,
    }
    out.append(ctl)


def _search(fits, lo=16, hi=160):
    if not fits(lo):
        return lo
    for _ in range(24):
        mid = (lo + hi) / 2
        if fits(mid):
            lo = mid
        else:
            hi = mid
    return int(lo)


def _title_fit(cfg, size, max_w):
    t = cfg["title"]
    text = t.get("text") or ""
    if not text:
        return size
    while size > 8:
        f = gfx.font(t["font"], size)
        if gfx.text_width(text, f, t.get("letter_spacing", 0) * size) <= max_w:
            break
        size -= 1
    return size


def _title_block(cfg, x, y, size, align, max_w):
    t = cfg["title"]
    sub = t.get("subtitle") or ""
    ss = int(t.get("subtitle_size") or max(8, round(size * 0.34)))
    f = gfx.font(t["font"], size)
    cap = gfx.cap_height(f)
    sub_cap = gfx.cap_height(gfx.font(t["subtitle_font"], ss)) if sub else 0
    gap = size * 0.32 if sub else 0
    return {"x": x, "y": y, "size": size, "sub_size": ss, "align": align, "cap": cap,
            "sub_y": y + cap + gap, "h": cap + gap + sub_cap, "max_w": max_w}


# ---------------------------------------------------------------- modes
def default_size(cfg, mode):
    if mode == "pedal":
        n = len(cfg["knobs"]["items"])
        return [320, 500 if n <= 6 else 560]
    n = len(cfg["knobs"]["items"]) * 1.0 + len(cfg["toggles"]["items"]) * 0.6
    n += sum(0.9 for f in cfg["footswitches"]["items"] if f.get("style") == "stomp")
    return [int(clamp(round(60 + 126 * n), 420, 1100)), 260]


def compute(cfg):
    mode = cfg.get("layout") or "auto"
    size = cfg.get("size")
    if mode == "auto":
        mode = "pedal" if size and size[1] > size[0] * 1.1 else "rack"
    W, H = size or default_size(cfg, mode)
    lay = (_pedal if mode == "pedal" else _rack)(cfg, int(W), int(H))
    lay.update({"width": int(W), "height": int(H), "mode": mode})
    _apply_manual(cfg, lay)
    order = {"knobs": 0, "toggles": 1, "footswitches": 2, "leds": 3}
    lay["controls"].sort(key=lambda c: (order[c["kind"]], c["item"]["index"]))
    _place_jacks(cfg, lay)
    return lay


# ---------------------------------------------------------------- jacks
def jack_metrics(cfg, W, H):
    """(height, protrusion) of a jack seen from the side, logical px."""
    hj = int(cfg["jacks"].get("size") or clamp(round(min(W, H) * 0.18), 36, 76))
    return hj, int(round(hj * 0.21))


def _obstacles(cfg, lay):
    """Visible shapes of controls, their labels and the title block:
    ("circle", cx, cy, r) for knobs incl. their tick scale, ("rect", x0, y0, x1, y1) otherwise."""
    lab = cfg["labels"]
    obs = []
    for c in lay["controls"]:
        it = c["item"]
        if c["kind"] == "knobs":
            s = c["w"]
            tk = it.get("ticks") or {}
            r = s / 2
            if int(tk.get("count", 11) or 0) >= 2:
                if tk.get("style") == "dots":
                    r = s * 0.545 + 2.5 + 1.5 * max(0.8, s / 80)
                else:
                    r = s * (0.545 + 0.10 * float(tk.get("length", 1.0))) + 1
            if it.get("range_labels"):
                r = max(r, s * 0.66 + c["label"]["size"] * 0.6 if c["label"] else s * 0.7)
            obs.append(("circle", c["x"] + s / 2, c["y"] + s / 2, r))
        else:
            obs.append(("rect", c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"]))
        L = c["label"]
        if L:
            f = gfx.font(lab["font"], L["size"])
            w = gfx.text_width(L["text"], f, lab.get("spacing", 0) * L["size"])
            obs.append(("rect", L["x"] - w / 2, L["y"], L["x"] + w / 2, L["y"] + gfx.cap_height(f)))
    tb, t = lay.get("title"), cfg["title"]
    if tb:  # title and subtitle as separate rows
        bar = 10 if t.get("accent_bar") and tb["align"] == "left" else 0
        for text, fnt, size, sp, y in ((t.get("text"), t["font"], tb["size"], t.get("letter_spacing", 0), tb["y"]),
                                       (t.get("subtitle"), t["subtitle_font"], tb["sub_size"],
                                        t.get("subtitle_spacing", 0), tb["sub_y"])):
            if not text:
                continue
            f = gfx.font(fnt, size)
            w = gfx.text_width(text, f, sp * size)
            x0 = {"left": tb["x"], "center": tb["x"] - w / 2, "right": tb["x"] - w}[tb["align"]]
            obs.append(("rect", x0, y, x0 + w, y + gfx.cap_height(f)))
        if bar:
            obs.append(("rect", tb["x"] - bar, tb["y"] - 1, tb["x"] - bar + 4, tb["y"] + tb["h"] + 1))
    return obs


def _span(o, y0, y1):
    """Horizontal extent (xl, xr) of an obstacle within the band y0..y1, or None."""
    if o[0] == "rect":
        return (o[1], o[3]) if y0 < o[4] and y1 > o[2] else None
    _, cx, cy, r = o
    dy = 0.0 if y0 <= cy <= y1 else min(abs(cy - y0), abs(cy - y1))
    if dy >= r:
        return None
    hw = math.sqrt(r * r - dy * dy)
    return cx - hw, cx + hw


JACK_Y = {1: [0.45], 2: [0.30, 0.60]}  # default jack centers as a fraction of the body height


def _place_jacks(cfg, lay):
    """Jacks sit at fixed heights (JACK_Y or per-jack `y`). If a jack label would run into a knob,
    a label or the title, the body is widened symmetrically so the content keeps its place relative
    to the center and the labels get room at the sides."""
    j = cfg["jacks"]
    lay["jacks"] = None
    if not (j["left"] or j["right"]):
        return
    W, H, m = lay["width"], lay["height"], lay["margin"]
    hj, P = jack_metrics(cfg, W, H)
    lab = cfg["labels"]
    ls = int(j.get("label_size") or max(8, round(lay["label_size"] * 0.78)))
    f = gfx.font(lab["font"], ls)
    cap = gfx.cap_height(f)
    gap = max(4, round(m * 0.35)) + lay.get("side", 0)  # keep labels off wooden side cheeks
    px, py = 2, 1                                       # labels may come this close to other parts
    obstacles = _obstacles(cfg, lay)

    jacks, grow = [], 0.0
    for side in ("left", "right"):
        for it, fy in zip(j[side], JACK_Y.get(len(j[side]), [])):
            cy = float(it["y"]) if it.get("y") is not None else fy * H
            tw = gfx.text_width(it["label"], f, lab.get("spacing", 0) * ls)
            aw = cap * 0.85 if it.get("arrow") and it["dir"] != "none" else 0
            lw = tw + (aw + cap * 0.45 if aw and tw else aw)
            y0, y1 = cy - cap * 0.75, cy + cap * 0.75
            if lw:
                for q in obstacles:
                    sp = _span(q, y0 - py, y1 + py)
                    if sp is None:
                        continue
                    if side == "left":   # label spans [gap, gap + lw]; content moves right by e
                        need = gap + lw + px - sp[0]
                    else:                # label spans [W' - gap - lw, W' - gap], W' = W + 2e
                        need = sp[1] + px + gap + lw - W
                    grow = max(grow, need)
            jacks.append((it, cy, tw, aw, lw))

    e = int(math.ceil(grow)) if grow > 0 else 0
    if e:
        _shift_x(lay, e)
        lay["width"] = W = W + 2 * e
    out = []
    for it, cy, tw, aw, lw in jacks:
        x0 = gap if it["side"] == "left" else W - gap - lw
        out.append(dict(it, cy=cy, label_rect=(x0, cy - cap * 0.75, x0 + lw, cy + cap * 0.75),
                        arrow_w=aw, text_w=tw))
    lay["jacks"] = {"items": out, "h": hj, "p": P, "label_size": ls, "widened": e,
                    "pad_l": P if j["left"] else 0, "pad_r": P if j["right"] else 0}


def _shift_x(lay, dx):
    for c in lay["controls"]:
        c["x"] += dx
        if c["label"]:
            c["label"]["x"] += dx
    if lay.get("title"):
        lay["title"]["x"] += dx
    if lay.get("panel"):
        p = lay["panel"]
        lay["panel"] = [p[0], p[1], p[2] + 2 * dx, p[3]]  # panel stretches with the body


def _apply_manual(cfg, lay):
    for c in lay["controls"]:
        pos = c["item"].get("pos")
        if pos:
            dx, dy = pos[0] - c["x"], pos[1] - c["y"]
            c["x"], c["y"] = int(pos[0]), int(pos[1])
            if c["label"]:
                c["label"]["x"] += dx
                c["label"]["y"] += dy
    t = cfg["title"]
    if t.get("pos") and lay.get("title"):
        tb = lay["title"]
        dy = t["pos"][1] - tb["y"]
        tb["x"], tb["y"], tb["sub_y"] = t["pos"][0], t["pos"][1], tb["sub_y"] + dy
        tb["align"] = "left"


def _rack(cfg, W, H):
    ctx = Ctx(cfg)
    bg, t = cfg["background"], cfg["title"]
    m = int(clamp(round(min(W, H) * 0.075), 10, 28))
    side = round(W * 0.035) if bg.get("wood_sides") else 0
    x0, x1 = m + side, W - m - side

    fs_items = cfg["footswitches"]["items"]
    fs_header = [f for f in fs_items if f.get("placement") == "header" or
                 (f.get("placement", "auto") == "auto" and f.get("style") != "stomp")]
    fs_main = [f for f in fs_items if f not in fs_header]
    leds = cfg["leds"]["items"]
    has_header = bool(t.get("text") or t.get("subtitle") or fs_header or leds)
    hh = int(clamp(round(H * 0.25), 44, 90)) if has_header else 0
    footer_h = 14 if bg.get("footer") else 0

    out = []
    # header right side: buttons then leds (right to left)
    hx = x1
    for f in reversed(fs_header):
        w, h = part_size("footswitches", f, 0, "header", hh)
        hx -= w
        out.append({"kind": "footswitches", "item": f, "x": hx, "y": int((hh - h) / 2), "w": w, "h": h,
                    "label": None})
        hx -= m * 0.6
    if leds:
        lsz = int(clamp(round(hh * 0.15), 8, 11))
        for led in reversed(leds):
            w, h = part_size("leds", led, hh * 0.9)
            label = led.get("label") or ""
            cw = max(w, ctx.label_w(label, lsz) + lsz * 0.8)
            cx = hx - cw / 2
            cy = hh * (0.4 if label else 0.5)
            out.append({"kind": "leds", "item": led, "x": int(round(cx - w / 2)), "y": int(round(cy - h / 2)),
                        "w": w, "h": h,
                        "label": {"text": label, "x": cx, "y": cy + led_lens(w) * 0.9, "size": lsz}
                        if label else None})
            hx -= cw + m * 0.3

    # title
    title = None
    if t.get("text") or t.get("subtitle"):
        tx = x0 + (12 if bg.get("screws") and not side else 0) + (10 if t.get("accent_bar") else 0)
        max_w = max(40, hx - tx - m)
        align = t.get("align") or "left"
        size = int(t.get("size") or round(hh * 0.46))
        size = _title_fit(cfg, size, max_w)
        title = _title_block(cfg, tx, 0, size, align, max_w)
        title["y"] = (hh - title["h"]) / 2
        title["sub_y"] += title["y"]
        if align == "center":
            title["x"] = W / 2
        elif align == "right":
            title["x"] = hx - m

    # main area
    y0 = hh + m * 0.7
    y1 = H - m * 0.7 - footer_h
    avail_w, avail_h = x1 - x0, y1 - y0
    main = [("knobs", it) for it in cfg["knobs"]["items"]] + \
           [("toggles", it) for it in cfg["toggles"]["items"]] + \
           [("footswitches", it) for it in fs_main]
    if not has_header:
        main += [("leds", it) for it in leds]
        out = [c for c in out if c["kind"] != "leds"]

    def build(k):
        ls = ctx.label_size(k)
        cells = [_cell(ctx, kind, it, k, ls) for kind, it in main]
        return ls, cells

    def fits(k):
        ls, cells = build(k)
        rows = _wrap(cells, avail_w, 4)
        if rows is None:
            return False
        hs = [_row_h(r, ls)[1] for r in rows]
        return sum(hs) + m * 0.5 * (len(rows) - 1) <= avail_h * 0.94

    fixed = cfg["knobs"].get("size")
    k = int(fixed) if fixed else min(_search(fits), 128)
    panel = None
    if main:
        ls, cells = build(k)
        rows = _wrap(cells, avail_w, 99) or [cells]
        hs = [_row_h(r, ls)[1] for r in rows]
        gap = max(0.0, (avail_h - sum(hs)) / (len(rows) + 1))
        y = y0 + gap
        for r, h in zip(rows, hs):
            _place_row(r, x0, avail_w, y, ls, out)
            y += h + gap
        if bg.get("panel"):
            pm = m * (0.2 if bg.get("screws") else 0.55)
            panel = [x0 - pm, hh + pm if hh else pm, x1 + pm, H - pm - footer_h]
    else:
        ls = ctx.label_size(k)
    return {"controls": out, "title": title, "header": {"h": hh} if hh else None, "panel": panel,
            "knob_unit": k, "label_size": ls, "margin": m, "side": side}


def _pedal(cfg, W, H):
    ctx = Ctx(cfg)
    t = cfg["title"]
    m = int(clamp(round(W * 0.06), 10, 28))
    x0, avail_w = m, W - 2 * m
    knobs = cfg["knobs"]["items"]
    n = len(knobs)
    per_row = {0: 1, 1: 1, 2: 2, 4: 2}.get(n, 3 if n <= 9 else 4)

    tsize0 = int(t.get("size") or round(W * 0.15))
    tsize = _title_fit(cfg, tsize0, avail_w)
    tblock = _title_block(cfg, W / 2, 0, tsize, t.get("align") or "center", avail_w) \
        if (t.get("text") or t.get("subtitle")) else None

    def sections(k):
        ls = ctx.label_size(k)
        secs = []
        if knobs:
            cells = [_cell(ctx, "knobs", it, k, ls, tight=True) for it in knobs]
            rows = [cells[i:i + per_row] for i in range(0, n, per_row)]
            secs.append(("rows", rows))
        if tblock:
            secs.append(("title", None))
        for kind in ("toggles", "leds", "footswitches"):
            items = cfg[kind]["items"]
            if items:
                kk = k
                if kind == "footswitches":
                    kk = min(clamp(W * 0.28, 48, 120), avail_w / (len(items) * 1.35)) / 0.82
                if kind == "leds":
                    kk = clamp(W * 0.06, 8, 16) / 0.16
                cells = [_cell(ctx, kind, it, kk, ls) for it in items]
                secs.append(("rows", [cells]))
        return ls, secs

    def heights(ls, secs):
        hs = []
        for kind, rows in secs:
            if kind == "title":
                hs.append(tblock["h"])
            else:
                hs.append(sum(_row_h(r, ls)[1] for r in rows) + m * 0.3 * (len(rows) - 1))
        return hs

    def fits(k):
        ls, secs = sections(k)
        for kind, rows in secs:
            if kind == "rows" and any(sum(c["cell_w"] for c in r) > avail_w for r in rows):
                return False
        hs = heights(ls, secs)
        return sum(hs) + m * 0.6 * (len(hs) + 1) <= H - 2 * m

    fixed = cfg["knobs"].get("size")
    k = int(fixed) if fixed else min(_search(fits), 120)
    ls, secs = sections(k)
    hs = heights(ls, secs)
    gap = max(0.0, (H - 2 * m - sum(hs)) / (len(hs) + 1))
    y = m + gap
    out = []
    title = None
    for (kind, rows), h in zip(secs, hs):
        if kind == "title":
            title = dict(tblock)
            title["sub_y"] += y
            title["y"] = y
        else:
            yy = y
            for r in rows:
                _place_row(r, x0, avail_w, yy, ls, out)
                yy += _row_h(r, ls)[1] + m * 0.3
        y += h + gap
    return {"controls": out, "title": title, "header": None, "panel": None,
            "knob_unit": k, "label_size": ls, "margin": m, "side": 0}
