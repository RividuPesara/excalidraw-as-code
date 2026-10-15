from __future__ import annotations

import itertools
import math
import sys

# kind to fill, outline and hatch tone, all from open-color so they match the excalidraw picker
TONES = {
    "entry": ("#d0ebff", "#1864ab", "#74c0fc"),
    "service": ("#c3fae8", "#087f5b", "#63e6be"),
    "store": ("#ffe8cc", "#d9480f", "#ffc078"),
    "outside": ("#f3d9fa", "#862e9c", "#e599f7"),
    "gate": ("#fff3bf", "#8a6d00", "#ffe066"),
    "focus": ("#ffdeeb", "#a61e4d", "#faa2c1"),
    "alert": ("#ffe3e3", "#c92a2a", "#ffa8a8"),
    "plain": ("#f1f3f5", "#495057", "#ced4da"),
}

INK = {"head": "#1e1e1e", "body": "#343a40", "soft": "#495057", "wire": "#495057"}

SKETCH_TONES = {
    "entry": ("#a5d8ff", "#1971c2", "#4dabf7"),
    "service": ("#b2f2bb", "#2b8a3e", "#69db7c"),
    "store": ("#ffd8a8", "#d9480f", "#ffa94d"),
    "outside": ("#eebefa", "#9c36b5", "#da77f2"),
    "gate": ("#ffec99", "#8a6d00", "#ffd43b"),
    "focus": ("#d0bfff", "#6741d9", "#9775fa"),
    "alert": ("#ffc9c9", "#e03131", "#ff8787"),
    "plain": ("#e9ecef", "#343a40", "#ced4da"),
}

SKETCH_INK = {"head": "#1e1e1e", "body": "#1e1e1e", "soft": "#343a40", "wire": "#1e1e1e"}

NOTE = ("#fff3bf", "#e67700")

ZONE = ("#f8f9fa", "#868e96")

# machado 2009 full severity simulation matrices in linear rgb
CVD = {
    "deuteranopia": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "protanopia": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "tritanopia": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _linear(hex_: str) -> list[float]:
    h = hex_.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def luminance(hex_: str) -> float:
    r, g, b = _linear(hex_)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _lab(rgb: list[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def distance(a: str, b: str, vision: str | None = None) -> float:
    ra, rb = _linear(a), _linear(b)
    if vision:
        m = CVD[vision]
        ra, rb = ([max(0.0, min(1.0, sum(row[j] * c[j] for j in range(3)))) for row in m] for c in (ra, rb))
    return math.dist(_lab(ra), _lab(rb))


def report(tones: dict[str, tuple[str, str, str]] = TONES, background: str = "#ffffff") -> list[str]:
    problems = []
    for kind, (fill, stroke, hatch) in tones.items():
        if contrast(INK["head"], fill) < 4.5 or contrast(INK["head"], hatch) < 4.5:
            problems.append(f"{kind} label text under 4.5 to 1 on its fill")
        if contrast(stroke, background) < 3 or contrast(stroke, fill) < 3:
            problems.append(f"{kind} outline under 3 to 1 against the page or its fill")
    for vision in (None, *CVD):
        for (a, (fa, sa, _)), (b, (fb, sb, _)) in itertools.combinations(tones.items(), 2):
            # fills are pale so a smaller lab gap is already visible
            if distance(sa, sb, vision) < 4 and distance(fa, fb, vision) < 4:
                problems.append(f"{a} and {b} look alike with {vision or 'normal vision'}")
    return problems


if __name__ == "__main__":
    found = []
    for name, tones in (("sketch", SKETCH_TONES), ("clean", TONES)):
        print(name)
        for kind, (fill, stroke, hatch) in tones.items():
            print(f"  {kind:8} fill {fill} outline {stroke} hatch {hatch}  "
                  f"text {contrast(INK['head'], fill):4.1f}  outline {contrast(stroke, '#ffffff'):3.1f}")
        found += [f"{name} {p}" for p in report(tones)]
    for p in found:
        print(f"check {p}")
    sys.exit(1 if found else 0)
