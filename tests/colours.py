"""Colour maths shared by the tests: WCAG 2.x contrast (D-037, D-042) and the CIEDE2000 colour difference.

A reference computed independently of the page's `common.js CONTRAST`, so the tests can check it.
"""

from __future__ import annotations

import math
import re

NAMED = {"white": "#ffffff", "black": "#000000"}


def channels(color: str) -> tuple[float, float, float]:
    """(r, g, b) in 0..1 of '#rgb', '#rrggbb[aa]', 'rgb(...)' / 'rgba(...)' or white / black."""
    c = NAMED.get(color.strip().lower(), color.strip())
    if c.startswith("rgb"):
        r, g, b = (float(v) / 255 for v in re.findall(r"[\d.]+", c)[:3])
        return r, g, b
    h = c.removeprefix("#")
    h = "".join(x * 2 for x in h) if len(h) == 3 else h[:6]
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b


def _linear(v: float) -> float:
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    """The WCAG 2.x relative luminance of `color`."""
    r, g, b = (_linear(v) for v in channels(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """The WCAG 2.x contrast ratio of two colours."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _lab(color: str) -> tuple[float, float, float]:
    """CIE L*a*b* (D65) of an sRGB colour."""
    r, g, b = (_linear(v) for v in channels(color))
    xyz = (
        (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047,
        0.2126729 * r + 0.7151522 * g + 0.0721750 * b,
        (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883,
    )
    fx, fy, fz = (t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _hue(b: float, a: float) -> float:
    return math.degrees(math.atan2(b, a)) % 360 if (a or b) else 0.0


def ciede2000(c1: str, c2: str) -> float:
    """The CIEDE2000 difference of two sRGB colours (Sharma, Wu and Dalal, 2005; kL = kC = kH = 1)."""
    return delta_e2000(_lab(c1), _lab(c2))


def delta_e2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """The CIEDE2000 difference of two CIE L*a*b* colours."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c_bar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7)))
    a1p, a2p = a1 * (1 + g), a2 * (1 + g)
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p, h2p = _hue(b1, a1p), _hue(b2, a2p)
    dl, dc = l2 - l1, c2p - c1p
    dh = 0.0 if c1p * c2p == 0 else (h2p - h1p + 180) % 360 - 180
    dhh = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dh / 2))
    l_bar, cp_bar = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        h_bar = (h1p + h2p) / 2
    else:
        h_bar = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar))
        + 0.32 * math.cos(math.radians(3 * h_bar + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar - 63))
    )
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    sc, sh = 1 + 0.045 * cp_bar, 1 + 0.015 * cp_bar * t
    rt = (
        -2
        * math.sqrt(cp_bar**7 / (cp_bar**7 + 25**7))
        * math.sin(math.radians(60 * math.exp(-(((h_bar - 275) / 25) ** 2))))
    )
    return math.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dhh / sh) ** 2 + rt * (dc / sc) * (dhh / sh))
