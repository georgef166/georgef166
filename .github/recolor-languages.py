#!/usr/bin/env python3
"""Recolour the language pie chart in the generated 3D-contrib SVG.

The action paints each language with GitHub's own language colour (C++ pink,
HTML orange, ...), which clashes with the green-to-blue contribution palette.
There is no SETTING_JSON option for language colours, so rewrite them after
generation instead.

Colours are assigned by slice order, not by language name, so the ramp keeps
working as the language mix changes.

Usage: python3 .github/recolor-languages.py <svg-path>
"""
import colorsys
import re
import sys

# hue endpoints of the ramp, matching the contribution palette
BLUE = (215 / 360, 0.75, 0.55)   # h, s, l
GREEN = (136 / 360, 0.55, 0.45)

# language colours appear as legend swatches (fill="#rgb") and pie wedges
# (style="fill: #rgb"); this matches both and captures only the hex
COLOR_RE = re.compile(r'(?:fill="|style="fill:\s*)(#[0-9a-fA-F]{6})')


def _hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def ramp(n):
    if n <= 1:
        return [_hex(*GREEN)]
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(_hex(*(a + (b - a) * t for a, b in zip(BLUE, GREEN))))
    return out


def main(path):
    svg = open(path, encoding="utf-8").read()

    order, seen = [], set()
    for m in COLOR_RE.finditer(svg):
        key = m.group(1).lower()
        if key not in seen:
            seen.add(key)
            order.append(key)
    if not order:
        print("no language colours found - nothing to do")
        return 0

    mapping = dict(zip(order, ramp(len(order))))
    # rewrite only the captured hex, leaving the surrounding attribute intact
    svg = COLOR_RE.sub(lambda m: m.group(0).replace(m.group(1), mapping[m.group(1).lower()]), svg)

    open(path, "w", encoding="utf-8").write(svg)
    print(f"recoloured {len(order)} languages: "
          + ", ".join(f"{o} -> {n}" for o, n in mapping.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
