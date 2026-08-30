#!/usr/bin/env python3
"""Generates assets/avatar-dots.svg -- the profile photo rendered as a dot matrix
that draws itself in left-to-right, top-to-bottom scan order, holds, clears in the
same order, and loops.

Source image: assets/avatar.jpg  (refresh with: curl -L https://github.com/georgef166.png -o assets/avatar.jpg)
Run: python3 assets/build_avatar_dots.py
"""
import math
import os
import sys

from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))

# --- knobs --------------------------------------------------------------
GRID     = 70      # dots per side
CROP     = (50, 60, 330, 340)   # head-and-shoulders crop of the 460x460 avatar
SIZE     = 360     # rendered card size in px
INSET    = 16      # padding between card edge and the dot field
BG       = "#0d1117"
BORDER   = "#30363d"

CONTRAST   = 1.55
SATURATION = 1.00
BRIGHTNESS = 1.06

R_MIN, R_MAX = 0.42, 1.04   # dot radius as a fraction of half-cell
R_GAMMA      = 0.70         # <1 lifts the shadows so dark areas keep some dot
MIN_ALPHA    = 0.02         # drop dots dimmer than this (shrinks the file)
STRETCH      = (2.0, 98.0)  # percentiles mapped to black/white before sizing dots
VIGNETTE     = 0.85         # 0 = off; fades the corners so the face carries the frame
VIG_CENTER   = (0.45, 0.30)  # where the vignette is centred, as a fraction of the frame
VIG_INNER    = 0.34          # everything inside this radius is left at full strength

BUCKETS   = 150    # dots animate in this many staggered waves along the scan
BUILD_IN  = 5.60   # time for the portrait to draw in
HOLD      = 5.00   # time the finished portrait sits still
FADE_OUT  = 2.60   # time to clear away
REST      = 0.70   # blank beat before it redraws


def build(mode="color", out_name="avatar-dots.svg"):
    img = Image.open(os.path.join(HERE, "avatar.jpg")).convert("RGB").crop(CROP)
    img = ImageEnhance.Contrast(img).enhance(CONTRAST)
    img = ImageEnhance.Color(img).enhance(SATURATION)
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS)
    small = img.resize((GRID, GRID), Image.LANCZOS)
    px = small.load()

    field = SIZE - 2 * INSET
    cell = field / GRID
    half = cell / 2

    # stretch luminance across the percentile window so dot sizes use the full range
    lums = sorted((0.2126 * px[x, y][0] + 0.7152 * px[x, y][1] + 0.0722 * px[x, y][2]) / 255
                  for y in range(GRID) for x in range(GRID))
    lo = lums[int(len(lums) * STRETCH[0] / 100)]
    hi = lums[min(int(len(lums) * STRETCH[1] / 100), len(lums) - 1)]
    span = max(hi - lo, 1e-6)

    dots = []
    for gy in range(GRID):
        for gx in range(GRID):
            r, g, b = px[gx, gy]
            raw = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            lum = min(max((raw - lo) / span, 0.0), 1.0)
            if VIGNETTE:
                cx0, cy0 = VIG_CENTER[0] * (GRID - 1), VIG_CENTER[1] * (GRID - 1)
                d = math.hypot(gx - cx0, gy - cy0) / (GRID - 1)
                t = max(0.0, (d - VIG_INNER) / max(1.0 - VIG_INNER, 1e-6))
                v = max(0.0, 1.0 - VIGNETTE * t * t)
                lum *= v
                r, g, b = int(r * v), int(g * v), int(b * v)
            if lum < MIN_ALPHA:
                continue
            rad = half * (R_MIN + (R_MAX - R_MIN) * (lum ** R_GAMMA))
            cx = INSET + gx * cell + half
            cy = INSET + gy * cell + half
            if mode == "gray":
                v = int(round(255 * min(max((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255, 0.0), 1.0)))
                fill = f"#{v:02x}{v:02x}{v:02x}"
            elif mode == "color":
                fill = f"#{r:02x}{g:02x}{b:02x}"
            else:
                fill = None
            dots.append((gx, gy, cx, cy, rad, fill, lum))

    # scan order: left to right within a row, top row to bottom row
    ordered = sorted(dots, key=lambda d: (d[1], d[0]))

    total = round(BUILD_IN + HOLD + FADE_OUT + REST, 3)
    n = len(ordered)
    # contiguous slices, so each wave is the next run along the scan
    waves = [ordered[i * n // BUCKETS:(i + 1) * n // BUCKETS] for i in range(BUCKETS)]

    p = ['<?xml version="1.0" encoding="UTF-8"?>']
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
             f'viewBox="0 0 {SIZE} {SIZE}" role="img" '
             f'aria-label="Portrait of George Farag rendered as an animated dot matrix">')
    p.append(f'<rect x="1" y="1" width="{SIZE-2}" height="{SIZE-2}" rx="14" fill="{BG}" stroke="{BORDER}"/>')
    grp_fill = '' if mode in ("color", "gray") else ' fill="#e6edf3"'
    for i, wave in enumerate(waves):
        if not wave:
            continue
        t_in = BUILD_IN * (i / BUCKETS)
        t_out = BUILD_IN + HOLD + FADE_OUT * (i / BUCKETS)
        k_in, k_out = t_in / total, t_out / total
        k_out_end = min((t_out + FADE_OUT / BUCKETS * 6) / total, 0.999)
        # opacity="1" is the static fallback: no SMIL -> the finished portrait
        p.append(f'<g opacity="1"{grp_fill}>')
        p.append(f'<animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" '
                 f'values="0;0;1;1;0;0" '
                 f'keyTimes="0;{k_in:.5f};{min(k_in + 0.010, k_out):.5f};{k_out:.5f};{k_out_end:.5f};1" '
                 f'calcMode="linear"/>')
        body = []
        for _, _, cx, cy, rad, fill, _ in wave:
            f = f' fill="{fill}"' if fill else ''
            body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.2f}"{f}/>')
        p.append("".join(body))
        p.append('</g>')
    p.append('</svg>')

    out_path = os.path.join(HERE, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(p) + "\n")
    print(f"wrote {out_path}  ({len(dots)} dots, loop {total}s, "
          f"{os.path.getsize(out_path)//1024} KB)")


if __name__ == "__main__":
    build(mode=sys.argv[1] if len(sys.argv) > 1 else "gray",
          out_name=sys.argv[2] if len(sys.argv) > 2 else "avatar-dots.svg")
