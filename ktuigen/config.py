# -*- coding: utf-8 -*-
"""Config loading, normalization, theme merging and palette resolution."""
import copy
import json
import os
import re

import yaml

from .themes import DEFAULTS, LABEL_POOL, THEMES

SECTIONS = ("knobs", "toggles", "footswitches", "leds")
ALIASES = {"knob": "knobs", "toggle": "toggles", "footswitch": "footswitches", "led": "leds",
           "switches": "toggles", "bg": "background"}
ITEM_META = ("count", "labels", "items")


class Loader(yaml.SafeLoader):
    """YAML 1.2 style booleans: only true/false, so labels like ON / OFF / YES / NO stay strings."""


Loader.yaml_implicit_resolvers = {k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
                                  for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                             list("tTfF"))


def yaml_load(text):
    return yaml.load(text, Loader=Loader)


def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.lower().endswith(".json"):
        return json.loads(text) or {}
    return yaml_load(text) or {}


def deep_merge(base, over):
    if not isinstance(base, dict) or not isinstance(over, dict):
        return copy.deepcopy(over)
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = deep_merge(out[k], v) if k in out and isinstance(out[k], dict) and isinstance(v, dict) \
            else copy.deepcopy(v)
    return out


def normalize(cfg):
    """Expand shorthands of a user (partial) config."""
    cfg = dict(cfg or {})
    for a, k in ALIASES.items():
        if a in cfg:
            v = cfg.pop(a)
            cfg[k] = deep_merge(cfg.get(k, {}), v) if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    for k in SECTIONS:
        if k not in cfg:
            continue
        v = cfg[k]
        if v is None or v is False:
            v = {"count": 0}
        elif v is True:
            v = {"count": max(1, DEFAULTS[k]["count"])}
        elif isinstance(v, int):
            v = {"count": v}
        elif isinstance(v, str):
            v = {"labels": [s.strip() for s in v.split(",")]}
        elif isinstance(v, list):
            v = {"labels": v}
        v = dict(v)
        no_labels = v.get("labels") is False
        if no_labels:  # keep the (inherited) count, blank every label
            v["labels"] = [""]
        if "count" not in v and "labels" in v and not no_labels:
            v["count"] = len(v.get("labels") or [])
        if "count" not in v and isinstance(v.get("items"), list):
            v["count"] = len(v["items"])
        if isinstance(v.get("ticks"), bool):
            v["ticks"] = {"count": 11} if v["ticks"] else {"count": 0}
        cfg[k] = v
    if isinstance(cfg.get("jacks"), dict):
        cfg["jacks"] = {k: _jack_side(v) if k in ("left", "right") else v for k, v in cfg["jacks"].items()}
    if isinstance(cfg.get("title"), str):
        cfg["title"] = {"text": cfg["title"]}
    if isinstance(cfg.get("background"), str):
        cfg["background"] = {"style": cfg["background"]}
    if isinstance(cfg.get("size"), str):
        w, _, h = cfg["size"].lower().partition("x")
        cfg["size"] = [int(w), int(h)]
    return cfg


def _jack_side(v):
    """left/right shorthand: count | "A,B" | [str | dict] -> list of dicts."""
    if v is None or v is False:
        return []
    if isinstance(v, int):
        return [{"label": ""} for _ in range(v)]
    if isinstance(v, str):
        v = [s.strip() for s in v.split(",")]
    out = []
    for it in v:
        if isinstance(it, str):
            label, sep, d = it.rpartition(":")
            it = {"label": label, "dir": d.strip().lower()} if sep and d.strip().lower() in JACK_DIRS                 else {"label": it}
        out.append(dict(it))
    return out


JACK_DIRS = ("in", "out", "none")


def _jack_dir(label):
    toks = re.split(r"[^A-Z0-9]+", (label or "").upper())
    if any(t in ("IN", "INPUT") for t in toks):
        return "in"
    if any(t in ("OUT", "OUTPUT") for t in toks):
        return "out"
    return "none"


def expand_jacks(j):
    for side in ("left", "right"):
        items = []
        for i, it in enumerate(j.get(side) or []):
            d = dict(it)
            d["label"] = "" if d.get("label") is None else str(d["label"])
            d["dir"] = (d.get("dir") or _jack_dir(d["label"])).lower()
            if d["dir"] not in JACK_DIRS:
                raise ValueError(f"jacks.{side}[{i}].dir must be one of {JACK_DIRS}, got {d['dir']!r}")
            d.setdefault("arrow", j.get("arrow", True))
            d["index"], d["side"] = i, side
            items.append(d)
        if len(items) > 2:
            raise ValueError(f"jacks.{side}: at most 2 jacks per side (got {len(items)})")
        j[side] = items
    return j


def _resolve_refs(obj, palette):
    if isinstance(obj, dict):
        return {k: _resolve_refs(v, palette) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_refs(v, palette) for v in obj]
    if isinstance(obj, str) and obj.startswith("$"):
        key = obj[1:]
        if key not in palette:
            raise ValueError(f"unknown palette reference {obj!r}")
        return palette[key]
    return obj


def build(user=None, overrides=None):
    """DEFAULTS <- theme <- user config <- overrides  ->  resolved config."""
    user, overrides = normalize(user), normalize(overrides)
    theme = overrides.get("theme") or user.get("theme") or DEFAULTS["theme"]
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r} (available: {', '.join(THEMES)})")
    cfg = deep_merge(DEFAULTS, {k: v for k, v in THEMES[theme].items() if not k.startswith("_")})
    cfg = deep_merge(cfg, user)
    cfg = deep_merge(cfg, overrides)
    cfg["theme"] = theme
    palette = cfg.get("palette", {})
    cfg = _resolve_refs(cfg, palette)
    for k in SECTIONS:
        cfg[k]["items"] = expand_items(k, cfg[k])
    cfg["jacks"] = expand_jacks(cfg["jacks"])
    return cfg


def expand_items(kind, sec):
    """Per-control dicts: section-level keys as defaults, then items[i] overrides."""
    labels = list(sec.get("labels") or [])
    items = sec.get("items") or []
    if isinstance(items, dict):  # {index: overrides} (e.g. from --set knobs.items.1.size=100)
        lst = [{} for _ in range(max(int(i) for i in items) + 1)]
        for i, v in items.items():
            lst[int(i)] = v
        items = lst
    items = list(items)
    n = max(int(sec.get("count") or 0), 0)
    pool = [p for p in LABEL_POOL.get(kind, []) if p not in labels]
    if labels and not any(labels):
        pool = []  # explicitly unlabeled: keep the rest unlabeled too
    while len(labels) < n:
        labels.append(pool.pop(0) if pool else "" if labels and not any(labels) else
                      f"{kind[:-1].upper()} {len(labels) + 1}")
    base = {k: v for k, v in sec.items() if k not in ITEM_META}
    out = []
    for i in range(n):
        it = items[i] if i < len(items) else {}
        if isinstance(it, str):
            it = {"label": it}
        d = deep_merge(base, it)
        d.setdefault("label", labels[i] if i < len(labels) else "")
        d["label"] = "" if d["label"] is None else str(d["label"])
        d["index"] = i
        out.append(d)
    return out


def load(path=None, overrides=None):
    user = load_file(path) if path else {}
    if path and not os.path.isabs(str(user.get("output", ""))) and "output" in user:
        user["output"] = os.path.join(os.path.dirname(os.path.abspath(path)), user["output"])
    return build(user, overrides)
