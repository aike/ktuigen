# -*- coding: utf-8 -*-
"""Render all parts, write PNGs, layout.json and preview.png."""
import json
import os

from PIL import Image

from . import background, gfx, knob, layout, switches

RENDERERS = {
    "knobs": lambda it, w, h: knob.render(it, w),
    "toggles": switches.render_toggle,
    "footswitches": switches.render_footswitch,
    "leds": switches.render_led,
}
TYPE_NAME = {"knobs": "knob", "toggles": "toggle", "footswitches": "footswitch", "leds": "led"}
NON_VISUAL = {"label", "index", "pos", "default", "states", "file", "orientation", "range_labels", "ticks",
              "placement", "rel", "size"}


def _spec_key(kind, it, w, h):
    vis = {k: v for k, v in it.items() if k not in NON_VISUAL}
    return json.dumps([kind, w, h, vis], sort_keys=True, default=str)


def _default_frame(kind, it, n):
    d = it.get("default", 0)
    if kind in ("knobs", "leds"):
        return int(round(max(0.0, min(1.0, float(d))) * (n - 1)))
    return max(0, min(n - 1, int(d)))


def generate(cfg, out_dir=None, log=print):
    out_dir = out_dir or cfg.get("output") or "out"
    os.makedirs(out_dir, exist_ok=True)
    scale = int(cfg.get("scale") or 1)
    lay = layout.compute(cfg)
    jk = lay.get("jacks")
    ox = jk["pad_l"] if jk else 0  # enclosure offset inside the image (jacks stick out on the left)
    BW, H = lay["width"], lay["height"]
    W = BW + ox + (jk["pad_r"] if jk else 0)

    bg_file = cfg["background"].get("file", "background.png")
    bg = background.render(cfg, lay, scale)
    bg.save(os.path.join(out_dir, bg_file))
    written = [bg_file]

    cache, used_names = {}, set()
    controls = []
    preview = bg.copy()
    for c in lay["controls"]:
        kind, it = c["kind"], c["item"]
        w, h = c["w"], c["h"]
        key = _spec_key(kind, it, w, h)
        orient = it.get("orientation") or cfg.get("orientation", "vertical")
        if key not in cache:
            frames = RENDERERS[kind](it, w * scale, h * scale)
            name = it.get("file") or TYPE_NAME[kind] + ".png"
            stem, ext = os.path.splitext(name)
            i = 2
            while name in used_names:
                name = f"{stem}_{i}{ext}"
                i += 1
            used_names.add(name)
            cache[key] = {"frames": frames, "name": name, "files": {}}
        entry = cache[key]
        frames = entry["frames"]
        if orient not in entry["files"]:
            name = entry["name"]
            if entry["files"]:  # same part also requested in the other direction
                stem, ext = os.path.splitext(name)
                name = f"{stem}_{orient[0]}{ext}"
            gfx.strip(frames, orient).save(os.path.join(out_dir, name))
            entry["files"][orient] = name
            written.append(name)
        fi = _default_frame(kind, it, len(frames))
        preview.alpha_composite(frames[fi], ((c["x"] + ox) * scale, c["y"] * scale))
        rec = {
            "type": TYPE_NAME[kind], "index": it["index"], "label": it.get("label", ""),
            "file": entry["files"][orient],
            "x": c["x"] + ox, "y": c["y"], "width": w, "height": h,
            "frames": len(frames), "orientation": orient,
            "default": it.get("default", 0),
        }
        if kind == "knobs":
            rec.update({"start_angle": it.get("start_angle"), "end_angle": it.get("end_angle"),
                        "bipolar": bool(it.get("bipolar"))})
        if kind == "toggles":
            rec["positions"] = int(it.get("positions", 2))
        controls.append(rec)

    doc = {
        "generator": "ktuigen", "theme": cfg.get("theme"), "width": W, "height": H, "scale": scale,
        "mode": lay["mode"], "background": bg_file,
        "body": {"x": ox, "y": 0, "width": BW, "height": H},
        "note": "coordinates are logical px; image px = logical * scale. frame 0 = minimum / off",
        "controls": controls,
    }
    if jk:
        doc["jacks"] = [{
            "side": it["side"], "index": it["index"], "label": it["label"], "dir": it["dir"],
            "x": 0 if it["side"] == "left" else ox + BW, "y": int(round(it["cy"] - jk["h"] / 2)),
            "width": jk["p"], "height": jk["h"],
        } for it in jk["items"]]
    with open(os.path.join(out_dir, "layout.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    written.append("layout.json")
    if cfg.get("preview", True):
        preview.save(os.path.join(out_dir, "preview.png"))
        written.append("preview.png")
    log(f"ktuigen: {W}x{H} ({lay['mode']}, theme={cfg.get('theme')}, scale={scale}) -> {out_dir}")
    for n in written:
        log("  " + n)
    return doc

