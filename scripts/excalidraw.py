from __future__ import annotations

import json
import sys
from pathlib import Path

# kind name to light fill and outline
TONES = {
    "entry": ("#e3ecfb", "#2c56b8"),
    "service": ("#e6f4f1", "#1f7a6b"),
    "store": ("#e9f6e3", "#3b7d2a"),
    "outside": ("#f2e9fb", "#7140a8"),
    "gate": ("#fff4d6", "#9a6b00"),
    "focus": ("#ffe3d3", "#c4511f"),
    "alert": ("#fde4e4", "#b42d2d"),
    "plain": ("#f3f4f6", "#5b6472"),
}

# stronger tones so hatch lines stay visible on white
HATCH = {
    "entry": "#9db6ec",
    "service": "#8fcfc3",
    "store": "#a6d494",
    "outside": "#c7a6ea",
    "gate": "#f0cf6e",
    "focus": "#f5a77f",
    "alert": "#ee9a9a",
    "plain": "#c3c8d0",
}

# fill style by what the box is
FILLS = {
    "built": "solid",
    "external": "hachure",
    "planned": "cross-hatch",
    "legacy": "zigzag",
}

INK = {"head": "#1b2330", "body": "#3a4556", "soft": "#6b7686", "wire": "#505a6b"}

SIZE = {"head": 32, "section": 22, "label": 17, "note": 15, "tiny": 13}

GLYPH = 0.55
LEADING = 1.25


def measure(s: str, size: float) -> tuple[float, float]:
    lines = s.split("\n")
    return max(len(line) for line in lines) * size * GLYPH, len(lines) * size * LEADING


class Scene:
    def __init__(self, background: str = "#ffffff") -> None:
        self.elements: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.background = background
        self._seed = 7000

    def _add(self, id_: str, type_: str, x: float, y: float, w: float, h: float,
             stroke: str, bg: str = "transparent", **kw) -> dict:
        if id_ in self.by_id:
            raise ValueError(f"duplicate element id {id_!r}")
        self._seed += 1
        e = {
            "id": id_, "type": type_, "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid", "strokeWidth": 2,
            "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [], "roundness": None,
            "seed": self._seed, "version": 1, "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
        }
        e.update(kw)
        self.elements.append(e)
        self.by_id[id_] = e
        return e

    def _attach(self, parent_id: str, child_id: str, kind: str) -> None:
        parent = self.by_id[parent_id]
        parent["boundElements"] = (parent["boundElements"] or []) + [{"id": child_id, "type": kind}]

    def text(self, id_: str, x: float, y: float, s: str, size: float = SIZE["note"], ink: str = "soft",
             align: str = "left", container: str | None = None, width: float | None = None) -> dict:
        w, h = measure(s, size)
        e = self._add(id_, "text", x, y, width or w, h, INK.get(ink, ink),
                      text=s, originalText=s, fontSize=size, fontFamily=2, textAlign=align,
                      verticalAlign="middle" if container else "top", containerId=container,
                      lineHeight=LEADING, autoResize=True)
        if container:
            self._attach(container, id_, "text")
        return e

    def box(self, id_: str, x: float, y: float, w: float, h: float, label: str = "",
            kind: str = "service", state: str | None = None, size: float = SIZE["label"],
            shape: str = "rectangle") -> dict:
        fill, stroke = TONES[kind]
        state = state or ("external" if kind == "outside" else "built")
        style = FILLS[state]
        if style != "solid":
            fill = HATCH[kind]
        e = self._add(id_, shape, x, y, w, h, stroke, fill, fillStyle=style,
                      strokeStyle="dashed" if state == "planned" else "solid",
                      roundness={"type": 3} if shape == "rectangle" else {"type": 2})
        if label:
            _, th = measure(label, size)
            self.text(f"{id_}__label", x + 8, y + (h - th) / 2, label, size, "head", "center",
                      container=id_, width=w - 16)
        return e

    def zone(self, id_: str, x: float, y: float, w: float, h: float, title: str = "", note: str = "") -> dict:
        fill, stroke = TONES["plain"]
        e = self._add(id_, "rectangle", x, y, w, h, stroke, fill, strokeStyle="dashed", opacity=40,
                      roundness={"type": 3}, zone=True)
        # titles stay free so they never centre over the children
        if title:
            self.text(f"{id_}__title", x + 28, y + 16, title, SIZE["section"], "head")
        if note:
            self.text(f"{id_}__note", x + 28, y + 48, note, SIZE["note"], "soft")
        return e

    def bounds(self, id_: str) -> tuple[float, float, float, float]:
        e = self.by_id[id_]
        return e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"]

    def anchor(self, id_: str, side: str, t: float = 0.5) -> tuple[float, float]:
        x0, y0, x1, y1 = self.bounds(id_)
        return {
            "left": (x0, y0 + (y1 - y0) * t), "right": (x1, y0 + (y1 - y0) * t),
            "top": (x0 + (x1 - x0) * t, y0), "bottom": (x0 + (x1 - x0) * t, y1),
        }[side]

    def arrow(self, id_: str, points: list[tuple[float, float]], src: str | None = None, dst: str | None = None,
              label: str | None = None, style: str = "solid", label_at: tuple[float, float] | None = None,
              head: str | None = "arrow", tail: str | None = None) -> dict:
        x0, y0 = points[0]
        rel = [[px - x0, py - y0] for px, py in points]
        xs = [p[0] for p in rel]
        ys = [p[1] for p in rel]
        e = self._add(id_, "arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), INK["wire"],
                      strokeStyle=style, points=rel, lastCommittedPoint=None,
                      startBinding={"elementId": src, "focus": 0, "gap": 1} if src else None,
                      endBinding={"elementId": dst, "focus": 0, "gap": 1} if dst else None,
                      startArrowhead=tail, endArrowhead=head)
        for ref in (src, dst):
            if ref:
                self._attach(ref, id_, "arrow")
        if label:
            # the label hides the wire under its box so keep it text wide
            lw, _ = measure(label, SIZE["tiny"])
            lx, ly = label_at or ((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2)
            self.text(f"{id_}__label", lx - lw / 2, ly - 8, label, SIZE["tiny"], "body", "center",
                      container=id_, width=lw + 6)
        return e

    def connect(self, id_: str, src: str, dst: str, label: str | None = None, style: str = "solid",
                label_at: tuple[float, float] | None = None, head: str | None = "arrow") -> dict:
        sx0, sy0, sx1, sy1 = self.bounds(src)
        dx0, dy0, dx1, dy1 = self.bounds(dst)
        top, bot = max(sy0, dy0), min(sy1, dy1)
        left, right = max(sx0, dx0), min(sx1, dx1)
        # straight when the shapes share a band otherwise an L into the top or bottom
        if bot - top >= 12:
            y = (top + bot) / 2
            pts = [(sx1, y), (dx0, y)] if sx1 <= dx0 else [(sx0, y), (dx1, y)]
        elif right - left >= 12:
            x = (left + right) / 2
            pts = [(x, sy1), (x, dy0)] if sy1 <= dy0 else [(x, sy0), (x, dy1)]
        else:
            sy = (sy0 + sy1) / 2
            dx = (dx0 + dx1) / 2
            start = (sx1, sy) if dx > sx1 else (sx0, sy)
            end = (dx, dy0) if dy0 > sy else (dx, dy1)
            pts = [start, (dx, sy), end]
        return self.arrow(id_, pts, src, dst, label, style, label_at, head)

    def grid(self, prefix: str, labels: list[str], x: float, y: float, cols: int, w: float, h: float,
             gap_x: float = 32, gap_y: float = 24, kind: str = "service", state: str | None = None,
             size: float = SIZE["label"]) -> list[str]:
        ids = []
        for i, label in enumerate(labels):
            id_ = f"{prefix}{i}"
            self.box(id_, x + (i % cols) * (w + gap_x), y + (i // cols) * (h + gap_y), w, h, label,
                     kind, state, size)
            ids.append(id_)
        return ids

    def legend(self, x: float, y: float, states: list[str] | None = None) -> None:
        # one small swatch per fill style used in the diagram
        for i, state in enumerate(states or list(FILLS)):
            self.box(f"legend_{state}", x + i * 150, y, 36, 24, "", "plain", state)
            self.text(f"legend_{state}__text", x + i * 150 + 46, y + 3, state, SIZE["tiny"], "soft")

    def check(self) -> list[str]:
        problems = []
        shapes = [e for e in self.elements if e["type"] in ("rectangle", "ellipse", "diamond") and not e.get("zone")]
        for i, a in enumerate(shapes):
            ax0, ay0, ax1, ay1 = self.bounds(a["id"])
            for b in shapes[i + 1:]:
                bx0, by0, bx1, by1 = self.bounds(b["id"])
                if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                    problems.append(f"{a['id']} and {b['id']} overlap")
        for e in self.elements:
            if e["type"] == "text" and e.get("containerId") in self.by_id:
                parent = self.by_id[e["containerId"]]
                if parent["type"] == "arrow":
                    continue
                w, h = measure(e["text"], e["fontSize"])
                if w > parent["width"] - 12 or h > parent["height"] - 4:
                    problems.append(f"label does not fit in {parent['id']}")
            if e["type"] == "arrow":
                for ref, (px, py) in ((e["startBinding"], e["points"][0]), (e["endBinding"], e["points"][-1])):
                    if not ref:
                        continue
                    x0, y0, x1, y1 = self.bounds(ref["elementId"])
                    ax, ay = e["x"] + px, e["y"] + py
                    if x0 + 2 < ax < x1 - 2 and y0 + 2 < ay < y1 - 2:
                        problems.append(f"arrow {e['id']} stops inside {ref['elementId']}")
        return problems

    def save(self, path: str | Path) -> Path:
        for problem in self.check():
            print(f"check {problem}", file=sys.stderr)
        elements = [{k: v for k, v in e.items() if k != "zone"} for e in self.elements]
        doc = {"type": "excalidraw", "version": 2, "source": "excalidraw-as-code", "elements": elements,
               "appState": {"viewBackgroundColor": self.background, "gridSize": None}, "files": {}}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(f"wrote {path}")
        return path
