# -*- coding: utf-8 -*-
"""Built-in default configuration and theme presets.

A theme is a partial config merged over DEFAULTS. Strings beginning with '$'
refer to entries of the resolved `palette` (e.g. "$accent").
"""

DEFAULTS = {
    "theme": "dark",
    "output": "out",
    "scale": 1,                    # pixel density (2 = @2x images, layout.json stays logical)
    "orientation": "vertical",     # film strip direction for all parts (per part override possible)
    "layout": "auto",              # auto | rack | pedal
    "size": None,                  # [w, h]; None = decided by layout
    "preview": True,
    "palette": {
        "accent": "#f2a33c",
        "text": "#d6d8de",
        "text_dim": "#82868e",
    },
    "background": {
        "file": "background.png",
        "style": "brushed",        # solid | gradient | brushed | matte | metallic | wood | carbon | grid
        "colors": ["#31343b", "#17191d"],
        "texture": 0.5,
        "vignette": 0.25,
        "corner_radius": 0,
        "border": True,
        "header_line": True,
        "panel": True,
        "panel_color": "#0000003c",
        "panel_outline": "#5a5e6678",
        "panel_radius": 10,
        "screws": False,
        "screw_color": "#a4a8b0",
        "wood_sides": False,
        "wood_colors": ["#6b3e1f", "#3d2110"],
        "grid_color": "$accent",
        "footer": "",
        "footer_color": "$text_dim",
        "seed": 7,
    },
    "title": {
        "text": "KTUIGEN",
        "subtitle": "AUDIO EFFECT",
        "font": "modern",
        "size": None,
        "color": "$text",
        "gradient": None,          # e.g. ["#ffffff", "#9aa0aa"]
        "effects": ["emboss"],     # shadow | emboss | engrave | glow | outline | bevel
        "glow_color": "$accent",
        "outline_color": "#000000",
        "letter_spacing": 0.04,    # em
        "subtitle_font": "modern-label",
        "subtitle_size": None,
        "subtitle_color": "$text_dim",
        "subtitle_spacing": 0.28,
        "align": None,             # left | center | right (None = layout default)
        "accent_bar": True,
        "accent_color": "$accent",
        "pos": None,               # [x, y] of the title block (top-left), overrides layout
    },
    "labels": {
        "font": "modern-label",
        "size": None,
        "color": "$text",
        "dim_color": "$text_dim",
        "spacing": 0.08,
        "effects": [],
        "position": "below",       # below | above
    },
    "knobs": {
        "file": "knob.png",
        "count": 4,
        "labels": ["DRIVE", "TONE", "MIX", "LEVEL"],
        "items": [],
        "style": "modern",         # modern | pedal | vintage | flat | metal
        "size": None,
        "rel": 1.0,
        "frames": 101,
        "start_angle": -135,       # degrees from 12 o'clock, clockwise
        "end_angle": 135,
        "bipolar": False,
        "arc": True,
        "arc_color": "$accent",
        "arc_track_color": "#3a3d44",
        "arc_glow": False,
        "arc_width": 1.0,
        "body_color": "#2c2f35",
        "body_color2": "#686c76",
        "edge_color": "#15161a",
        "cap_color": "#3a3d44",
        "pointer": "line",         # line | dot | none
        "pointer_color": "#f0f2f6",
        "pointer_tip": "$accent",
        "ridges": 0,
        "shadow": 0.6,
        "highlight": 1.0,
        "ticks": {"count": 11, "major": [0, 5, 10], "color": "#a8acb4c8", "style": "lines", "length": 1.0},
        "range_labels": None,      # e.g. ["0", "10"]
        "default": 0.5,
    },
    "toggles": {
        "file": "toggle.png",
        "count": 0,
        "labels": [],
        "items": [],
        "style": "bat",            # bat | slide | pill
        "positions": 2,
        "axis": "vertical",
        "size": None,
        "states": None,            # e.g. ["OFF", "ON"] printed beside the switch
        "metal_color": "#c9cdd3",
        "body_color": "#1c1d21",
        "on_color": "$accent",
        "off_color": "#4a4d55",
        "thumb_color": "#e8eaee",
        "default": 0,
    },
    "footswitches": {
        "file": "footswitch.png",
        "count": 1,
        "labels": ["BYPASS"],
        "items": [],
        "style": "button",         # button | stomp
        "size": None,
        "color": "#2a2c32",
        "on_color": "#3a332b",
        "metal_color": "#d0d4da",
        "led": True,
        "led_color": "$accent",
        "text_color": "$text",
        "text_dim": "$text_dim",
        "placement": "auto",       # auto | header | main
        "default": 0,
    },
    "leds": {
        "file": "led.png",
        "count": 0,
        "labels": [],
        "items": [],
        "style": "round",          # round | square
        "color": "$accent",
        "bezel": "chrome",         # chrome | black | none
        "size": None,
        "frames": 2,
        "default": 1,
    },
    "jacks": {
        "left": [],                # each: "L-IN" | "SEND:out" | {label, dir: in|out|none, arrow, y}
        "right": [],
        "size": None,              # jack height (logical px); None = auto
        "metal_color": "#c9cdd3",
        "label_size": None,
        "label_color": "$text",
        "arrow": True,             # triangle beside the label: IN points inward, OUT points outward
        "arrow_color": None,       # None = label_color
    },
}

LABEL_POOL = {
    "knobs": ["DRIVE", "TONE", "MIX", "LEVEL", "TIME", "FEEDBACK", "DEPTH", "RATE",
              "ATTACK", "RELEASE", "THRESHOLD", "RATIO", "LOW", "MID", "HIGH", "OUTPUT"],
    "toggles": ["MODE", "SYNC", "BRIGHT", "HI-CUT", "STEREO", "BOOST"],
    "footswitches": ["BYPASS", "BOOST", "TAP", "HOLD"],
    "leds": ["ON", "CLIP", "SIGNAL", "SYNC"],
}

THEMES = {
    "dark": {
        "_description": "Dark brushed metal studio plugin with amber accents (default)",
    },
    "light": {
        "_description": "Clean light UI with flat knobs and blue accents",
        "palette": {"accent": "#2f7cf6", "text": "#2b2f36", "text_dim": "#7a808a"},
        "background": {"style": "matte", "colors": ["#f1f2f5", "#dcdfe4"], "texture": 0.25,
                       "vignette": 0.08, "panel_color": "#ffffff8c", "panel_outline": "#b9bec6aa"},
        "title": {"effects": ["engrave"], "letter_spacing": 0.02},
        "knobs": {"style": "flat", "body_color": "#ffffff", "body_color2": "#f3f4f6", "edge_color": "#c3c8cf",
                  "arc_track_color": "#cdd1d7", "pointer": "dot", "pointer_color": "$accent", "shadow": 0.35,
                  "ticks": {"color": "#8a9099b0"}},
        "toggles": {"style": "pill", "off_color": "#c3c8cf", "thumb_color": "#ffffff"},
        "footswitches": {"color": "#f7f8fa", "on_color": "#e9f1ff", "text_color": "$text", "text_dim": "$text_dim"},
        "leds": {"bezel": "none"},
    },
    "vintage": {
        "_description": "Vintage tube gear: dark faceplate, gold lettering, ivory knobs, wood cheeks",
        "palette": {"accent": "#e0b25c", "text": "#e6cf9a", "text_dim": "#a8916a"},
        "background": {"style": "matte", "colors": ["#2e2620", "#1a1511"], "texture": 0.55, "vignette": 0.35,
                       "screws": True, "screw_color": "#c9b890", "wood_sides": True, "header_line": True,
                       "panel": False},
        "title": {"font": "serif-bold", "subtitle_font": "serif-label", "effects": ["emboss"],
                  "gradient": ["#f4dc9c", "#c0913f"], "letter_spacing": 0.02, "accent_bar": False,
                  "subtitle_spacing": 0.32},
        "labels": {"font": "serif-label", "spacing": 0.1},
        "knobs": {"style": "vintage", "arc": False, "body_color": "#e6dcc3", "body_color2": "#fbf6ea",
                  "edge_color": "#8c7c5c", "cap_color": "#c9a24f", "pointer_color": "#2a1d12",
                  "ridges": 36, "shadow": 0.75, "ticks": {"color": "#d8bf86d0", "style": "dots"}},
        "toggles": {"style": "bat", "metal_color": "#d6d0c2"},
        "footswitches": {"style": "stomp", "metal_color": "#d8d3c8"},
        "leds": {"color": "#ff5a2a"},
    },
    "pedal": {
        "_description": "Stomp box: powder coated enclosure, black knurled knobs, stomp switch",
        "layout": "pedal",
        "palette": {"accent": "#ff2a2a", "text": "#f4f5f7", "text_dim": "#c4cad4"},
        "background": {"style": "metallic", "colors": ["#2463ad", "#163e72"], "texture": 0.6, "vignette": 0.2,
                       "corner_radius": 18, "panel": False, "header_line": False},
        "title": {"text": "KTUIGEN", "subtitle": "OVERDRIVE", "font": "heavy", "effects": ["shadow"],
                  "letter_spacing": 0.0, "accent_bar": False, "subtitle_spacing": 0.35},
        "labels": {"font": "sans-bold", "spacing": 0.06},
        "knobs": {"count": 3, "labels": ["LEVEL", "TONE", "DRIVE"], "style": "pedal", "arc": False,
                  "body_color": "#141416", "body_color2": "#3a3b40", "cap_color": "#202124",
                  "pointer_color": "#f4f4f4", "ridges": 28, "shadow": 0.8,
                  "ticks": {"color": "#f4f5f7c0"}},
        "toggles": {"style": "bat"},
        "footswitches": {"style": "stomp", "labels": [""]},
        "leds": {"count": 1, "labels": [""], "color": "#ff2a2a"},
    },
    "neon": {
        "_description": "Synthwave: deep purple, perspective grid, glowing logo and cyan arcs",
        "palette": {"accent": "#29e3ff", "text": "#e3d8ff", "text_dim": "#9a86d6"},
        "background": {"style": "grid", "colors": ["#1d1238", "#0a0618"], "texture": 0.6, "vignette": 0.35,
                       "grid_color": "#ff4fd8", "panel_color": "#05021060", "panel_outline": "#8a5cff70"},
        "title": {"font": "condensed", "gradient": ["#ffd1f4", "#ff4fd8", "#8a5cff"], "effects": ["glow"],
                  "glow_color": "#ff4fd8", "letter_spacing": 0.08, "accent_bar": False},
        "labels": {"font": "modern-label", "spacing": 0.14},
        "knobs": {"style": "modern", "arc_glow": True, "body_color": "#1a1530", "body_color2": "#463c6e",
                  "edge_color": "#0b0818", "arc_track_color": "#2c2450", "pointer_color": "#e9e2ff",
                  "ticks": {"color": "#9a86d6a0"}},
        "toggles": {"style": "pill", "off_color": "#3a3060", "thumb_color": "#f0eaff"},
        "footswitches": {"color": "#1e1838", "on_color": "#1e2a44", "led_color": "$accent"},
        "leds": {"bezel": "black"},
    },
}
