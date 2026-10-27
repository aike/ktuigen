# -*- coding: utf-8 -*-
"""ktuigen command line interface."""
import argparse
import sys

import yaml

from . import config, generator
from .themes import THEMES


def _set(d, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        k = config.ALIASES.get(k, k)
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value


def _csv(s):
    return [x.strip() for x in s.split(",")]


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog="ktuigen",
        description="Generate GUI images (background, knob film strips, switches, LEDs) for effect plugins.")
    ap.add_argument("config", nargs="?", help="YAML / JSON config file (optional)")
    ap.add_argument("-o", "--output", help="output directory (default: out)")
    ap.add_argument("-t", "--theme", help="theme preset: " + ", ".join(THEMES))
    ap.add_argument("--size", help="background size WxH, e.g. 600x260")
    ap.add_argument("--layout", choices=["auto", "rack", "pedal"])
    ap.add_argument("--title", help="logo title text")
    ap.add_argument("--subtitle", help="subtitle text")
    ap.add_argument("--knobs", help="number of knobs, or comma separated labels")
    ap.add_argument("--toggles", help="number of toggle switches, or comma separated labels")
    ap.add_argument("--footswitches", "--footswitch", dest="footswitches",
                    help="number of footswitches, or comma separated labels")
    ap.add_argument("--leds", help="number of LEDs, or comma separated labels")
    ap.add_argument("--jacks-left", help="jacks on the left side (0-2): count or labels, e.g. 'L-OUT,R-OUT' "
                    "or 'SEND:out' (IN/OUT arrow is inferred from the label or given after ':')")
    ap.add_argument("--jacks-right", help="jacks on the right side (0-2), same format as --jacks-left")
    ap.add_argument("--orientation", choices=["vertical", "horizontal"], help="film strip direction")
    ap.add_argument("--frames", type=int, help="knob animation frames")
    ap.add_argument("--knob-size", type=int, help="knob size in px")
    ap.add_argument("--accent", help="accent color, e.g. '#ff8800'")
    ap.add_argument("--scale", type=int, help="pixel density (2 = @2x)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override any config value, e.g. --set knobs.style=metal --set background.texture=0.8")
    ap.add_argument("--no-preview", action="store_true", help="do not write preview.png")
    ap.add_argument("--list-themes", action="store_true", help="list theme presets and exit")
    ap.add_argument("--dump-config", action="store_true", help="print the fully resolved config and exit")
    return ap.parse_args(argv)


def _count_or_labels(v):
    return int(v) if v.isdigit() else _csv(v)


def main(argv=None):
    a = parse_args(argv)
    if a.list_themes:
        for k, v in THEMES.items():
            print(f"{k:10s} {v.get('_description', '')}")
        return 0

    ov = {}
    if a.output:
        ov["output"] = a.output
    if a.theme:
        ov["theme"] = a.theme
    if a.size:
        ov["size"] = a.size
    if a.layout:
        ov["layout"] = a.layout
    if a.title is not None:
        _set(ov, "title.text", a.title)
    if a.subtitle is not None:
        _set(ov, "title.subtitle", a.subtitle)
    for sec in ("knobs", "toggles", "footswitches", "leds"):
        v = getattr(a, sec)
        if v is not None:
            ov[sec] = _count_or_labels(v)
    for side in ("left", "right"):
        v = getattr(a, "jacks_" + side)
        if v is not None:
            _set(ov, "jacks." + side, _count_or_labels(v))
    ov = config.normalize(ov)
    if a.orientation:
        ov["orientation"] = a.orientation
    if a.frames:
        _set(ov, "knobs.frames", a.frames)
    if a.knob_size:
        _set(ov, "knobs.size", a.knob_size)
    if a.accent:
        _set(ov, "palette.accent", a.accent)
    if a.scale:
        ov["scale"] = a.scale
    if a.no_preview:
        ov["preview"] = False
    for s in a.set:
        k, sep, v = s.partition("=")
        if not sep:
            print(f"ktuigen: --set expects KEY=VALUE, got {s!r}", file=sys.stderr)
            return 2
        _set(ov, k.strip(), config.yaml_load(v))

    try:
        cfg = config.load(a.config, ov)
    except (ValueError, OSError, yaml.YAMLError) as e:
        print(f"ktuigen: {e}", file=sys.stderr)
        return 2
    if a.dump_config:
        dump = {k: v for k, v in cfg.items()}
        yaml.safe_dump(dump, sys.stdout, sort_keys=False, allow_unicode=True)
        return 0
    generator.generate(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
