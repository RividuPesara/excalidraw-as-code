from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import library
import route
from metrics import ASCII, MONO, WIDTHS
from palette import INK, NOTE, SKETCH_INK, SKETCH_TONES, TONES, ZONE

# lighter tint per kind for zones that belong to one role
ZONE_TINT = {
    "entry": "#e7f5ff", "service": "#e6fcf5", "store": "#fff4e6", "outside": "#f8f0fc",
    "gate": "#fff9db", "focus": "#fff0f6", "alert": "#fff5f5", "plain": ZONE[0],
}

FILLS = {"built": "solid", "external": "hachure", "planned": "cross-hatch", "legacy": "zigzag"}

SIZE = {"head": 32, "section": 22, "label": 17, "note": 15, "tiny": 13}

FONTS = {"sans": 2, "hand": 5, "code": 3, "rounded": 6, "comic": 8, "virgil": 1}
LINE_HEIGHT = {1: 1.25, 2: 1.15, 3: 1.2, 5: 1.25, 6: 1.25, 8: 1.25, 9: 1.15}

# every head kroki draws, crowfoot names migrate to cardinality ones when opened in excalidraw
HEADS = {"arrow", "bar", "circle", "circle_outline", "triangle", "triangle_outline", "diamond",
         "diamond_outline", "crowfoot_one", "crowfoot_many", "crowfoot_one_or_many"}
HEAD_ALIAS = {"dot": "circle", "one": "crowfoot_one", "many": "crowfoot_many",
              "one_or_many": "crowfoot_one_or_many"}

PAD = 5
MIN_GAP = 16
CAP = 14


def measure(s: str, size: float, font: int = 2) -> tuple[float, float]:
    widths = WIDTHS.get(font)
    best = 0.0
    lines = s.split("\n")
    for line in lines:
        w = 0.0
        for ch in line:
            if font in MONO:
                w += MONO[font] * (2 if ord(ch) >= 0x2E80 else 1)
            elif ch in ASCII:
                w += widths[ord(ch) - 32]
            else:
                w += 1.0 if ord(ch) >= 0x2E80 else 0.62
        best = max(best, w)
    return best * size, len(lines) * size * LINE_HEIGHT.get(font, 1.25)


def _head(name: str | None) -> str | None:
    if name is None:
        return None
    name = HEAD_ALIAS.get(name, name)
    if name not in HEADS:
        raise ValueError(f"arrowhead {name!r} does not render through kroki, use one of {sorted(HEADS)}")
    return name


class Scene:
    def __init__(self, style: str = "sketch", background: str = "#ffffff", font: str | int | None = None) -> None:
        if style not in ("clean", "sketch"):
            raise ValueError("style is clean or sketch")
        self.elements: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.background = background
        self.roughness = 1 if style == "sketch" else 0
        self.font = FONTS.get(font, font) if font else (5 if style == "sketch" else 2)
        self.tones = SKETCH_TONES if style == "sketch" else TONES
        self.ink = SKETCH_INK if style == "sketch" else INK
        self.wires: list[dict] = []
        self.problems_found: list[str] = []
        self._stuck: list[str] = []
        self._laid_out = False
        self._seed = 7000

    # elements

    def _add(self, id_: str, type_: str, x: float, y: float, w: float, h: float, stroke: str,
             bg: str = "transparent", before: str | None = None, **kw) -> dict:
        if id_ in self.by_id:
            raise ValueError(f"duplicate element id {id_!r}")
        self._seed += 1
        e = {
            "id": id_, "type": type_, "x": x, "y": y, "width": w, "height": h, "angle": 0,
            "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid", "strokeWidth": 2,
            "strokeStyle": "solid", "roughness": self.roughness, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "seed": self._seed, "version": 1, "isDeleted": False,
            "boundElements": None, "updated": 1, "link": None, "locked": False,
        }
        e.update(kw)
        if before is not None:
            self.elements.insert(self.elements.index(self.by_id[before]), e)
        else:
            self.elements.append(e)
        self.by_id[id_] = e
        self._laid_out = False
        return e

    def _attach(self, parent_id: str, child_id: str, kind: str) -> None:
        parent = self.by_id[parent_id]
        parent["boundElements"] = (parent["boundElements"] or []) + [{"id": child_id, "type": kind}]

    def text(self, id_: str, x: float, y: float, s: str, size: float | None = None, ink: str = "soft",
             align: str = "left", font: str | int | None = None, before: str | None = None, **kw) -> dict:
        size = size or SIZE["note"]
        fam = FONTS.get(font, font) if font else self.font
        w, h = measure(s, size, fam)
        # x is the anchor of the alignment so centred and right text grow from it
        left = x - w / 2 if align == "center" else (x - w if align == "right" else x)
        return self._add(id_, "text", left, y, w, h, self.ink.get(ink, ink), before=before, text=s, originalText=s,
                         fontSize=size, fontFamily=fam, textAlign=align, verticalAlign="top",
                         containerId=None, lineHeight=LINE_HEIGHT.get(fam, 1.25), autoResize=True, **kw)

    def title(self, heading: str, subtitle: str | None = None, x: float = 40, y: float = 0) -> float:
        self.text("title", x, y, heading, SIZE["head"], "head")
        bottom = y + measure(heading, SIZE["head"], self.font)[1]
        if subtitle:
            self.text("subtitle", x, bottom + 6, subtitle, SIZE["note"], "soft")
            bottom += 6 + measure(subtitle, SIZE["note"], self.font)[1]
        return bottom

    def _label(self, parent: str, s: str, size: float, ink: str = "head", align: str = "center",
               valign: str = "middle", font: int | None = None) -> dict:
        box = self.by_id[parent]
        fam = font or self.font
        w, h = measure(s, size, fam)
        x = box["x"] + (box["width"] - w) / 2 if align == "center" else box["x"] + PAD + 4
        y = box["y"] + (box["height"] - h) / 2 if valign == "middle" else box["y"] + PAD + 4
        e = self._add(f"{parent}__label", "text", x, y, w, h, self.ink.get(ink, ink), text=s, originalText=s,
                      fontSize=size, fontFamily=fam, textAlign=align, verticalAlign=valign, containerId=parent,
                      lineHeight=LINE_HEIGHT.get(fam, 1.25), autoResize=True, groupIds=list(box["groupIds"]))
        self._attach(parent, e["id"], "text")
        return e

    def box(self, id_: str, x: float, y: float, w: float | None = None, h: float | None = None, label: str = "",
            kind: str = "service", state: str | None = None, shape: str = "rectangle",
            size: float | None = None) -> dict:
        size = size or SIZE["label"]
        fill, stroke, hatch = self.tones[kind]
        state = state or ("external" if kind == "outside" else "built")
        style = FILLS[state]
        if w is None or h is None:
            tw, th = measure(label, size, self.font)
            # ellipses and diamonds only hold text in their middle
            grow = {"rectangle": 1.0, "ellipse": 1.42, "diamond": 2.0, "cylinder": 1.0}[shape]
            w = w or max(120, math.ceil(((tw + 2 * PAD + 24) * grow) / 10) * 10)
            h = h or max(56, math.ceil(((th + 2 * PAD + 20) * grow) / 4) * 4) + (3 * CAP if shape == "cylinder" else 0)
        if shape == "cylinder":
            return self._cylinder(id_, x, y, w, h, label, size, fill if style == "solid" else hatch, stroke, style,
                                  state == "planned")
        e = self._add(id_, shape, x, y, w, h, stroke, hatch if style != "solid" else fill, fillStyle=style,
                      strokeStyle="dashed" if state == "planned" else "solid",
                      strokeWidth=4 if kind == "focus" else 2,
                      roundness={"type": 3} if shape == "rectangle" else {"type": 2}, _shape=True)
        if label:
            self._label(id_, label, size)
        return e

    def _cylinder(self, id_: str, x: float, y: float, w: float, h: float, label: str, size: float, bg: str,
                  stroke: str, style: str, dashed: bool) -> dict:
        line = "dashed" if dashed else "solid"
        self._add(f"{id_}__bot", "ellipse", x, y + h - 2 * CAP, w, 2 * CAP, stroke, bg, fillStyle=style,
                  strokeStyle=line, _owner=id_)
        if style != "solid":
            # hatching is see through so a white mask hides the back of the bottom rim
            self._add(f"{id_}__mask", "rectangle", x, y + CAP, w, h - 2 * CAP, "transparent", self.background,
                      strokeWidth=0, _owner=id_)
        # no outline on the body so it hides the back of the bottom rim
        self._add(f"{id_}__body", "rectangle", x, y + CAP, w, h - 2 * CAP, "transparent", bg, fillStyle=style,
                  strokeWidth=0, _owner=id_)
        for side, sx in (("l", x), ("r", x + w)):
            self.line(f"{id_}__{side}", [(sx, y + CAP), (sx, y + h - CAP)], line, stroke)["_owner"] = id_
        self._add(f"{id_}__top", "ellipse", x, y, w, 2 * CAP, stroke, bg, fillStyle=style, strokeStyle=line,
                  _owner=id_)
        # an invisible box over the whole drum carries the label and the wire bindings
        e = self._add(id_, "rectangle", x, y, w, h, "transparent", "transparent", strokeWidth=0, _shape=True,
                      _cylinder=True)
        if label:
            lab = self._label(id_, label, size)
            lab["y"] += CAP / 2
        return e

    def grid(self, prefix: str, labels: list[str], x: float, y: float, cols: int, w: float, h: float,
             gap_x: float = 32, gap_y: float = 24, kind: str = "service", state: str | None = None,
             size: float | None = None) -> list[str]:
        ids = []
        for i, label in enumerate(labels):
            id_ = f"{prefix}{i}"
            self.box(id_, x + (i % cols) * (w + gap_x), y + (i // cols) * (h + gap_y), w, h, label, kind, state,
                     size=size)
            ids.append(id_)
        return ids

    def zone(self, id_: str, x: float, y: float, w: float, h: float, title: str = "", note: str = "",
             kind: str = "plain", before: str | None = None) -> dict:
        stroke = ZONE[1] if kind == "plain" else self.tones[kind][2]
        e = self._add(id_, "rectangle", x, y, w, h, stroke, ZONE_TINT[kind], before=before, strokeStyle="dashed",
                      roundness={"type": 3}, _zone=True)
        after = self.elements[self.elements.index(e) + 1]["id"] if before else None
        # titles stay free text so excalidraw never centres them over the children
        if title:
            self.text(f"{id_}__title", x + 24, y + 16, title, SIZE["section"], "head", before=after, _owner=id_)
        if note:
            ny = y + 20 + measure(title or "x", SIZE["section"], self.font)[1]
            self.text(f"{id_}__note", x + 24, ny, note, SIZE["note"], "soft", before=after, _owner=id_)
        return e

    def zone_around(self, id_: str, ids: list[str], title: str = "", note: str = "", pad: float = 32,
                    kind: str = "plain", heading: str = "top") -> dict:
        x0, y0, x1, y1 = self._union(ids)
        first = min(ids, key=lambda i: self.elements.index(self.by_id[i]))
        tw = max(measure(title, SIZE["section"], self.font)[0] if title else 0,
                 measure(note, SIZE["note"], self.font)[0] if note else 0)
        if heading == "side":
            # a heading column on the left keeps the top free for wires coming down into the children
            left = tw + 48 if tw else pad
            return self.zone(id_, x0 - left, y0 - pad, x1 - x0 + left + pad, y1 - y0 + 2 * pad, title, note, kind,
                             before=first)
        top = pad
        if title:
            top = 16 + measure(title, SIZE["section"], self.font)[1] + 16
        if note:
            top += measure(note, SIZE["note"], self.font)[1] + 4
        top = max(top, pad)
        return self.zone(id_, x0 - pad, y0 - top, x1 - x0 + 2 * pad, y1 - y0 + top + pad, title, note, kind,
                         before=first)

    def frame(self, id_: str, x: float, y: float, w: float, h: float, name: str = "") -> dict:
        # excalidraw draws the frame name above its top edge
        return self._add(id_, "frame", x, y, w, h, "#bbb", roughness=0, name=name or None, _frame=True,
                         before=self.elements[0]["id"] if self.elements else None)

    def note(self, id_: str, x: float, y: float, s: str, w: float | None = None, size: float | None = None) -> dict:
        size = size or SIZE["note"]
        tw, th = measure(s, size, self.font)
        w = w or tw + 2 * PAD + 24
        e = self._add(id_, "rectangle", x, y, w, th + 2 * PAD + 20, NOTE[1], NOTE[0], roundness=None, _shape=True)
        self._label(id_, s, size, "body", "left", "top")
        return e

    def table(self, id_: str, x: float, y: float, name: str, fields: list[str], kind: str = "store",
              w: float | None = None) -> dict:
        fill, stroke, _ = self.tones[kind]
        size = SIZE["note"]
        body = "\n".join(fields)
        tw = max(measure(name, SIZE["label"], self.font)[0], measure(body, size, self.font)[0])
        w = w or math.ceil((tw + 40) / 10) * 10
        head = 40
        bh = measure(body, size, self.font)[1] if fields else 0
        e = self._add(id_, "rectangle", x, y, w, head + bh + 24, stroke, "#ffffff", groupIds=[id_],
                      roundness={"type": 3}, _shape=True)
        self._add(f"{id_}__head", "rectangle", x, y, w, head, stroke, fill, groupIds=[id_],
                  roundness={"type": 3}, _owner=id_)
        self._label(f"{id_}__head", name, SIZE["label"])
        if fields:
            self.text(f"{id_}__fields", x + 14, y + head + 12, body, size, "body", groupIds=[id_], _owner=id_)
        return e

    def icon(self, id_: str, source: str, item: str | int, x: float, y: float, size: float = 64,
             label: str | None = None, keep_text: bool = False) -> dict:
        _, els = library.pick(source, item)
        # an invisible box carries the bindings since arrows cannot bind to a group
        hit = self._add(id_, "rectangle", x, y, size, size, "transparent", groupIds=[id_], _shape=True,
                        _icon=True)
        for e in library.place(els, x, y, size, size, id_, keep_text):
            if e["id"] in self.by_id:
                raise ValueError(f"duplicate element id {e['id']!r}")
            e["_owner"] = id_
            self.elements.append(e)
            self.by_id[e["id"]] = e
        if label:
            self.text(f"{id_}__caption", x + size / 2, y + size + 6, label, SIZE["tiny"] + 1, "body", "center",
                      groupIds=[id_])
        return hit

    def line(self, id_: str, points: list[tuple[float, float]], style: str = "solid", color: str | None = None,
             fill: str | None = None, width: float = 2) -> dict:
        x0, y0 = points[0]
        rel = [[px - x0, py - y0] for px, py in points]
        closed = fill is not None
        return self._add(id_, "line", x0, y0, max(p[0] for p in rel) - min(p[0] for p in rel),
                         max(p[1] for p in rel) - min(p[1] for p in rel), color or self.ink["wire"],
                         fill or "transparent", strokeStyle=style, strokeWidth=width, points=rel,
                         lastCommittedPoint=None, startBinding=None, endBinding=None, startArrowhead=None,
                         endArrowhead=None, polygon=closed)

    def legend(self, x: float, y: float, states: list[str] | None = None,
               kinds: dict[str, str] | None = None) -> float:
        cx = x
        for state in states or []:
            self.box(f"legend_{state}", cx, y, 36, 24, "", "plain", state)
            self.text(f"legend_{state}__text", cx + 46, y + 4, state, SIZE["tiny"], "soft")
            cx += 46 + measure(state, SIZE["tiny"], self.font)[0] + 32
        for kind, name in (kinds or {}).items():
            self.box(f"legend_{kind}", cx, y, 36, 24, "", kind)
            self.text(f"legend_{kind}__text", cx + 46, y + 4, name, SIZE["tiny"], "soft")
            cx += 46 + measure(name, SIZE["tiny"], self.font)[0] + 32
        return cx

    # wires

    def arrow(self, id_: str, points: list[tuple[float, float]], src: str | None = None, dst: str | None = None,
              label: str | None = None, style: str = "solid", label_at: tuple[float, float] | None = None,
              head: str | None = "arrow", tail: str | None = None, elbow: bool = False, width: float = 2,
              label_size: float | None = None) -> dict:
        e = self._wire(id_, src, dst, label, style, head, tail, elbow, width, label_size)
        self._set_points(e, [tuple(p) for p in points])
        self.wires.append({"id": id_, "fixed": True, "label_at": label_at})
        return e

    def connect(self, id_: str, src: str, dst: str, label: str | None = None, style: str = "solid",
                head: str | None = "arrow", tail: str | None = None, sides: tuple[str | None, str | None] = (None, None),
                elbow: bool = False, width: float = 2, label_size: float | None = None) -> dict:
        for ref in (src, dst):
            if ref not in self.by_id:
                raise KeyError(f"connect {id_} names {ref!r} which does not exist yet")
        e = self._wire(id_, src, dst, label, style, head, tail, elbow, width, label_size)
        self.wires.append({"id": id_, "fixed": False, "src": src, "dst": dst, "sides": sides})
        return e

    def _wire(self, id_, src, dst, label, style, head, tail, elbow, width, label_size=None) -> dict:
        if style not in ("solid", "dashed", "dotted"):
            raise ValueError("style is solid, dashed or dotted")
        e = self._add(id_, "arrow", 0, 0, 1, 0, self.ink["wire"], strokeStyle=style, strokeWidth=width,
                      points=[[0, 0], [1, 0]], lastCommittedPoint=None,
                      startBinding={"elementId": src, "focus": 0, "gap": 1} if src else None,
                      endBinding={"elementId": dst, "focus": 0, "gap": 1} if dst else None,
                      startArrowhead=_head(tail), endArrowhead=_head(head), elbowed=elbow,
                      roundness=None)
        for ref in (src, dst):
            if ref:
                self._attach(ref, id_, "arrow")
        if label:
            size = label_size or SIZE["tiny"]
            lw, lh = measure(label, size, self.font)
            t = self._add(f"{id_}__label", "text", 0, 0, lw, lh, self.ink["body"], text=label, originalText=label,
                          fontSize=size, fontFamily=self.font, textAlign="center", verticalAlign="middle",
                          containerId=id_, lineHeight=LINE_HEIGHT.get(self.font, 1.25), autoResize=True)
            self._attach(id_, t["id"], "text")
        return e

    def _set_points(self, e: dict, pts: list[tuple[float, float]]) -> None:
        x0, y0 = pts[0]
        rel = [[round(px - x0, 2), round(py - y0, 2)] for px, py in pts]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        e.update(x=x0, y=y0, points=rel, width=max(xs) - min(xs), height=max(ys) - min(ys))

    def sequence(self, prefix: str, x: float, y: float, actors: list[str], messages: list[tuple],
                 gap: float = 240, step: float = 56, kind: str = "service", numbered: bool = True) -> float:
        size = SIZE["label"]
        w = max(140, max(measure(a, size, self.font)[0] for a in actors) + 40)
        h = max(56, max(measure(a, size, self.font)[1] for a in actors) + 24)
        names = {a.split("\n")[0]: i for i, a in enumerate(actors)}
        cx = [x + i * gap + w / 2 for i in range(len(actors))]
        bottom = y + h + step * (len(messages) + 1)
        for i in range(len(actors)):
            self.line(f"{prefix}life{i}", [(cx[i], y + h), (cx[i], bottom)], "dashed", ZONE[1])
        for i, a in enumerate(actors):
            self.box(f"{prefix}{i}", x + i * gap, y, w, h, a, kind)
        for j, msg in enumerate(messages):
            a, b, text = msg[0], msg[1], msg[2]
            style = msg[3] if len(msg) > 3 else "solid"
            ia, ib = (names[v] if isinstance(v, str) else v for v in (a, b))
            yy = y + h + step * (j + 1)
            text = f"{j + 1}  {text}" if numbered else text
            if ia == ib:
                pts = [(cx[ia], yy - 12), (cx[ia] + 44, yy - 12), (cx[ia] + 44, yy + 12), (cx[ia], yy + 12)]
                self.arrow(f"{prefix}m{j}", pts, style=style)
                self.text(f"{prefix}m{j}__text", cx[ia] + 54, yy - 9, text, SIZE["tiny"], "body")
                continue
            self.arrow(f"{prefix}m{j}", [(cx[ia], yy), (cx[ib], yy)], style=style)
            # labels hug the sender so a long message never runs over a lifeline in between
            lx = cx[ia] + 10 if ib > ia else cx[ia] - 10
            ly = yy - measure(text, SIZE["tiny"], self.font)[1] - 4
            self.text(f"{prefix}m{j}__text", lx, ly, text, SIZE["tiny"], "body", "left" if ib > ia else "right")
        return bottom

    def arrange(self, layers: list[list[str]], x: float, y: float, direction: str = "right",
                gap: float = 160, spread: float = 40, sweeps: int = 6) -> None:
        # barycenter ordering keeps connected boxes level with each other so wires run straight
        links = [(w["src"], w["dst"]) for w in self.wires if not w["fixed"]]
        layers = [list(l) for l in layers]
        original = {n: i for l in layers for i, n in enumerate(l)}

        def pos(layer: list[str]) -> dict[str, int]:
            return {n: i for i, n in enumerate(layer)}

        def crossings(order: list[list[str]]) -> int:
            total = 0
            for a, b in zip(order, order[1:]):
                pa, pb = pos(a), pos(b)
                es = [(pa[s], pb[d]) for s, d in links if s in pa and d in pb]
                es += [(pa[d], pb[s]) for s, d in links if d in pa and s in pb]
                total += sum(1 for i, e in enumerate(es) for f in es[i + 1:] if (e[0] - f[0]) * (e[1] - f[1]) < 0)
            return total

        best = [list(l) for l in layers]
        for sweep in range(sweeps):
            rng = range(1, len(layers)) if sweep % 2 == 0 else range(len(layers) - 2, -1, -1)
            for i in rng:
                ref = pos(layers[i - 1] if sweep % 2 == 0 else layers[i + 1])
                cur = pos(layers[i])

                def bary(n: str) -> float:
                    near = [ref[d] for s, d in links if s == n and d in ref] + [ref[s] for s, d in links if d == n and s in ref]
                    return sum(near) / len(near) if near else cur[n]

                layers[i].sort(key=lambda n: (bary(n), cur[n]))
            if crossings(layers) < crossings(best):
                best = [list(l) for l in layers]
        across = direction == "right"
        centre: dict[str, float] = {}
        at = x if across else y
        degree = {n: sum(n in l for l in links) for layer in best for n in layer}
        for k, layer in enumerate(best):
            rs = {n: self.bounds(n) for n in layer}
            size = {n: (r[3] - r[1]) if across else (r[2] - r[0]) for n, r in rs.items()}
            if k == 0:
                run = y if across else x
                for n in layer:
                    centre[n] = run + size[n] / 2
                    run += size[n] + spread
            else:
                # each box lines up with what feeds it and the busiest box gets first pick
                want = {}
                for n in layer:
                    near = [centre[o] for a, b in links for o, m in ((a, b), (b, a)) if m == n and o in centre]
                    want[n] = sum(near) / len(near) if near else None
                order = sorted(layer, key=lambda n: (want[n] is None, -degree[n], original[n]))
                placed: dict[str, float] = {}
                for n in order:
                    i = layer.index(n)
                    lo, hi = -math.inf, math.inf
                    for j in range(i - 1, -1, -1):
                        if layer[j] in placed:
                            lo = placed[layer[j]] + (size[layer[j]] + size[n]) / 2 + spread * (i - j) + sum(size[layer[q]] for q in range(j + 1, i))
                            break
                    for j in range(i + 1, len(layer)):
                        if layer[j] in placed:
                            hi = placed[layer[j]] - (size[layer[j]] + size[n]) / 2 - spread * (j - i) - sum(size[layer[q]] for q in range(i + 1, j))
                            break
                    guess = want[n] if want[n] is not None else (lo if lo > -math.inf else (hi if hi < math.inf else (y if across else x) + size[n] / 2))
                    placed[n] = max(lo, min(hi, guess)) if lo <= hi else lo
                for a, b in zip(layer, layer[1:]):
                    need = placed[a] + (size[a] + size[b]) / 2 + spread
                    placed[b] = max(placed[b], need)
                centre.update(placed)
        # aligning to parents can push a layer past the requested corner so pull everything back
        floor = (y if across else x) - min(centre[n] - ((self.bounds(n)[3] - self.bounds(n)[1]) if across else
                                                         (self.bounds(n)[2] - self.bounds(n)[0])) / 2 for n in centre)
        if floor > 0:
            centre = {n: c + floor for n, c in centre.items()}
        for k, layer in enumerate(best):
            rs = {n: self.bounds(n) for n in layer}
            thick = max((r[2] - r[0]) if across else (r[3] - r[1]) for r in rs.values())
            for n in layer:
                r = rs[n]
                w, h = r[2] - r[0], r[3] - r[1]
                if across:
                    self.move(n, at + (thick - w) / 2, centre[n] - h / 2)
                else:
                    self.move(n, centre[n] - w / 2, at + (thick - h) / 2)
            at += thick + gap

    def move(self, id_: str, x: float, y: float) -> None:
        e = self.by_id[id_]
        dx, dy = x - e["x"], y - e["y"]
        for o in self.elements:
            if o is e or o.get("_owner") == id_ or o.get("containerId") == id_ or id_ in (o.get("groupIds") or []):
                if o["id"] in self._wire_ids():
                    continue
                o["x"] += dx
                o["y"] += dy
        self._laid_out = False

    def highlight(self, id_: str, color: str = "#e64980", width: float = 4) -> None:
        e = self.by_id[id_]
        for o in [e] + [o for o in self.elements if o.get("_owner") == id_ and o["type"] != "text"]:
            if o["strokeColor"] != "transparent":
                o["strokeColor"] = color
                # hairline glyph parts keep their weight or small icons fill in solid
                if o["strokeWidth"] > 1.5:
                    o["strokeWidth"] = width - 1 if o["type"] == "arrow" else width

    # geometry

    def bounds(self, id_: str) -> tuple[float, float, float, float]:
        e = self.by_id[id_]
        if e.get("points"):
            xs = [e["x"] + p[0] for p in e["points"]]
            ys = [e["y"] + p[1] for p in e["points"]]
            return min(xs), min(ys), max(xs), max(ys)
        l, t, r, b = e.get("_extent", (0, 0, 0, 0))
        return e["x"] - l, e["y"] - t, e["x"] + e["width"] + r, e["y"] + e["height"] + b

    def _union(self, ids: list[str]) -> tuple[float, float, float, float]:
        rs = [self.bounds(i) for i in ids]
        for i in ids:
            cap = self.by_id.get(f"{i}__caption")
            if cap:
                rs.append(self.bounds(cap["id"]))
        return min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)

    def anchor(self, id_: str, side: str, t: float = 0.5) -> tuple[float, float]:
        e = self.by_id[id_]
        return route.outline_point(self.bounds(id_), e["type"] if e["type"] != "frame" else "rectangle", side, t)

    def _shapes(self) -> list[dict]:
        return [e for e in self.elements if e.get("_shape")]

    def _free_texts(self) -> list[dict]:
        return [e for e in self.elements if e["type"] == "text" and not e.get("containerId")]

    def _blockers(self) -> list[dict]:
        return self._shapes() + [e for e in self._free_texts() if not self.by_id.get(e.get("_owner") or "", {}).get("_shape")]

    def _frame_names(self) -> list[tuple[str, tuple[float, float, float, float]]]:
        out = []
        for e in self.elements:
            if e["type"] == "frame" and e.get("name"):
                w, h = measure(e["name"], 14, 2)
                out.append((e["id"], (e["x"], e["y"] - h - 6, e["x"] + w, e["y"] - 2)))
        return out

    # layout

    def layout(self) -> None:
        if self._laid_out:
            return
        blockers = self._blockers()
        rects = [self.bounds(b["id"]) for b in blockers] + [r for _, r in self._frame_names()]
        index = {b["id"]: i for i, b in enumerate(blockers)}
        router = route.Router(rects)
        for z in (e for e in self.elements if e.get("_zone") or e.get("_frame")):
            x0, y0, x1, y1 = self.bounds(z["id"])
            router.soft += [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1))]
        for w in self.wires:
            if w["fixed"]:
                router.commit(self._points(w["id"]))
        todo = [w for w in self.wires if not w["fixed"]]

        # first pass picks the sides, second pass spreads the ports along them
        fixed = list(router.taken)
        router.taken = []
        chosen = {w["id"]: self._route(router, index, w, None) for w in todo}
        ports = self._spread(todo, chosen)
        router.taken = fixed
        self._stuck = []
        for w in todo:
            pts = self._route(router, index, w, ports.get(w["id"]))
            if not pts:
                self._stuck.append(w["id"])
                pts = chosen[w["id"]] or self._fallback(w)
            self._set_points(self.by_id[w["id"]], pts)
            router.commit(pts)
        # rip up any wire that still crosses and route it again against all the others
        for _ in range(3):
            better = False
            for w in todo:
                mine = route.segments(self._points(w["id"]))
                rest = [s for o in self.wires if o is not w for s in route.segments(self._points(o["id"]))]
                before = sum(route.crosses(a, b) for a in mine for b in rest)
                if not before:
                    continue
                router.taken = rest
                pts = self._route(router, index, w, ports.get(w["id"]))
                if pts and sum(route.crosses(a, b) for a in route.segments(pts) for b in rest) < before:
                    self._set_points(self.by_id[w["id"]], pts)
                    better = True
            if not better:
                break
        self._place_labels(rects)
        self._laid_out = True

    def _wire_ids(self) -> set[str]:
        return {w["id"] for w in self.wires}

    def _points(self, id_: str) -> list[tuple[float, float]]:
        e = self.by_id[id_]
        return [(e["x"] + p[0], e["y"] + p[1]) for p in e["points"]]

    def _route(self, router: route.Router, index: dict, w: dict, ports: dict | None) -> list | None:
        src, dst = self.by_id[w["src"]], self.by_id[w["dst"]]
        rs, rd = self.bounds(src["id"]), self.bounds(dst["id"])
        if src is dst:
            x0, y0, x1, y1 = rs
            label = self.by_id.get(f"{w['id']}__label")
            out = max(40, label["width"] + 44) if label else 40
            return [(x1, y0 + (y1 - y0) * 0.3), (x1 + out, y0 + (y1 - y0) * 0.3), (x1 + out, y0 + (y1 - y0) * 0.7),
                    (x1, y0 + (y1 - y0) * 0.7)]
        want_s, want_d = w["sides"]
        if ports:
            (ss, ts), (sd, td) = ports["start"], ports["end"]
            sides_s, sides_d = {ss: ts}, {sd: td}
        else:
            sides_s = {s: 0.5 for s in route.SIDES if not want_s or s == want_s}
            sides_d = {s: 0.5 for s in route.SIDES if not want_d or s == want_d}
        shape_s = src["type"] if src["type"] in ("ellipse", "diamond") else "rectangle"
        shape_d = dst["type"] if dst["type"] in ("ellipse", "diamond") else "rectangle"
        starts = {s: route.outline_point(rs, shape_s, s, t) for s, t in sides_s.items()}
        ends = {s: route.outline_point(rd, shape_d, s, t) for s, t in sides_d.items()}
        gap = {"right": rd[0] - rs[2], "left": rs[0] - rd[2], "bottom": rd[1] - rs[3], "top": rs[1] - rd[3]}
        # stubs are measured from the bounding box so curved outlines still leave the box straight
        flip = {"right": "left", "left": "right", "top": "bottom", "bottom": "top"}
        out, inn = 20.0, 40.0
        for s in starts:
            if 0 < gap[s] < out + inn + 8 and flip[s] in ends:
                out, inn = gap[s] * 0.35, gap[s] * 0.5
        lead_s = {s: abs(route.side_point(rs, s, sides_s[s])[0] - p[0]) + abs(route.side_point(rs, s, sides_s[s])[1] - p[1])
                  for s, p in starts.items()}
        lead_d = {s: abs(route.side_point(rd, s, sides_d[s])[0] - p[0]) + abs(route.side_point(rd, s, sides_d[s])[1] - p[1])
                  for s, p in ends.items()}
        skip = tuple(index[i] for i in (src["id"], dst["id"]) if i in index)
        best = None
        face_s, face_d = route.facing(rs, rd), route.facing(rd, rs)
        # sides that point away are only tried when nothing facing works
        pairs = [(s, d) for s in starts for d in ends]
        near = [(s, d) for s, d in pairs if face_s[s] + face_d[d] < 3 * route.BEND]
        for group in (near, pairs):
            for s, d in group:
                pts = router.route(rs, rd, {s: starts[s]}, {d: ends[d]}, face_s, face_d,
                                           out + lead_s[s], inn + lead_d[d], skip)
                if pts:
                    cost = self._cost(router, pts) + face_s[s] + face_d[d]
                    if best is None or cost < best[0]:
                        best = (cost, pts)
            if best:
                break
        return best[1] if best else None

    def _cost(self, router: route.Router, pts: list) -> float:
        segs = route.segments(pts)
        return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) + router._penalty((a, b)) for a, b in segs) + route.BEND * (len(segs) - 1)

    def _fallback(self, w: dict) -> list:
        rs, rd = self.bounds(w["src"]), self.bounds(w["dst"])
        return [route.side_point(rs, "right", 0.5), route.side_point(rd, "left", 0.5)]

    def _spread(self, todo: list[dict], chosen: dict) -> dict:
        ends: dict[tuple[str, str], list] = {}
        sides = {}
        for w in todo:
            pts = chosen.get(w["id"])
            if not pts or w["src"] == w["dst"]:
                continue
            ss = self._side_of(w["src"], pts[0])
            sd = self._side_of(w["dst"], pts[-1])
            sides[w["id"]] = (ss, sd)
            ends.setdefault((w["src"], ss), []).append((w, "start", pts[1] if len(pts) > 2 else pts[-1]))
            ends.setdefault((w["dst"], sd), []).append((w, "end", pts[-2] if len(pts) > 2 else pts[0]))
        ports: dict[str, dict] = {w: {"start": (s, 0.5), "end": (d, 0.5)} for w, (s, d) in sides.items()}
        # diamonds and ellipses read best when each wire owns a vertex so extra wires move to a free side
        for (shape, side), group in list(ends.items()):
            if self.by_id[shape]["type"] not in ("ellipse", "diamond") or len(group) < 2:
                continue
            for w, which, _ in group[1:]:
                fx, fy = self._far(w, which)
                x0, y0, x1, y1 = self.bounds(shape)
                free = [d for d in route.SIDES if not ends.get((shape, d))]
                if not free:
                    break
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                pick = max(free, key=lambda d: route.NORMAL[d][0] * (fx - cx) + route.NORMAL[d][1] * (fy - cy))
                ends[(shape, pick)] = [(w, which, None)]
                group.remove((w, which, _)) if (w, which, _) in group else None
                ports[w["id"]][which] = (pick, 0.5)
        for (shape, side), group in ends.items():
            if len(group) < 2:
                continue
            nx, ny = route.NORMAL[side]
            tx, ty = (1, 0) if side in ("top", "bottom") else (0, 1)
            x0, y0, x1, y1 = self.bounds(shape)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

            # wires that bend away sooner take the outer ports so neighbours never cross
            def turn(g: tuple) -> float:
                fx, fy = self._far(g[0], g[1])
                return math.atan2((fx - cx) * tx + (fy - cy) * ty, (fx - cx) * nx + (fy - cy) * ny)

            group.sort(key=turn)
            n = len(group)
            for i, (w, which, _) in enumerate(group):
                ports[w["id"]][which] = (side, (i + 1) / (n + 1))
        for w in todo:
            if w["id"] not in ports:
                continue
            (ss, ts), (sd, td) = ports[w["id"]]["start"], ports[w["id"]]["end"]
            alone_s = len(ends[(w["src"], ss)]) == 1
            alone_d = len(ends[(w["dst"], sd)]) == 1
            pair = {ss, sd}
            if alone_s and alone_d and pair in ({"left", "right"}, {"top", "bottom"}):
                # a lone wire between facing sides lines up its two ends so it can run straight
                rs, rd = self.bounds(w["src"]), self.bounds(w["dst"])
                axis = 1 if ss in ("left", "right") else 0
                lo, hi = max(rs[axis], rd[axis]), min(rs[axis + 2], rd[axis + 2])
                if hi - lo > 16:
                    mid = (lo + hi) / 2
                    ts = (mid - rs[axis]) / (rs[axis + 2] - rs[axis])
                    td = (mid - rd[axis]) / (rd[axis + 2] - rd[axis])
                    ports[w["id"]] = {"start": (ss, ts), "end": (sd, td)}
        return ports

    def _far(self, w: dict, which: str) -> tuple[float, float]:
        other = w["dst"] if which == "start" else w["src"]
        x0, y0, x1, y1 = self.bounds(other)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def _side_of(self, id_: str, p: tuple[float, float]) -> str:
        x0, y0, x1, y1 = self.bounds(id_)
        d = {"left": abs(p[0] - x0), "right": abs(p[0] - x1), "top": abs(p[1] - y0), "bottom": abs(p[1] - y1)}
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # curved outlines sit inside the box so judge by direction from the centre too
        if self.by_id[id_]["type"] in ("ellipse", "diamond"):
            dx, dy = (p[0] - cx) / max(1, x1 - x0), (p[1] - cy) / max(1, y1 - y0)
            return ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("bottom" if dy > 0 else "top")
        return min(d, key=d.get)

    def _place_labels(self, rects: list) -> None:
        placed: list = []
        borders = []
        for z in (e for e in self.elements if e.get("_zone") or e.get("_frame")):
            x0, y0, x1, y1 = self.bounds(z["id"])
            borders += [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1))]
        for w in self.wires:
            label = self.by_id.get(f"{w['id']}__label")
            if not label:
                continue
            e = self.by_id[w["id"]]
            pts = route.simplify(self._points(w["id"]))
            others = [s for o in self.wires if o["id"] != w["id"] for s in route.segments(self._points(o["id"]))]
            others += [s for l in self.elements if l["type"] == "line" and not l.get("_owner")
                       for s in route.segments(self._points(l["id"]))]
            lw, lh = label["width"], label["height"]
            if w.get("label_at"):
                seg, p = self._project(pts, w["label_at"])
                score = 0
            else:
                seg, p, score = route.place_label(pts, lw, lh, [route.inflate(r, 6) for r in rects] + placed,
                                                  others, borders,
                                                  bool(e["endArrowhead"]), bool(e["startArrowhead"]))
            new, frac = route.center_label(pts, seg, p, (lw if route.is_h(route.segments(pts)[seg]) else lh) / 2)
            self._set_points(e, new)
            label.update(x=p[0] - lw / 2, y=p[1] - lh / 2, labelPosition=round(frac, 4), _cramped=score >= 2000)
            placed.append((p[0] - lw / 2 - 4, p[1] - lh / 2 - 2, p[0] + lw / 2 + 4, p[1] + lh / 2 + 2))

    def _project(self, pts: list, at: tuple[float, float]) -> tuple[int, tuple[float, float]]:
        best = None
        for i, (a, b) in enumerate(route.segments(pts)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = dx * dx + dy * dy or 1
            t = max(0.05, min(0.95, ((at[0] - a[0]) * dx + (at[1] - a[1]) * dy) / ln))
            p = (a[0] + dx * t, a[1] + dy * t)
            d = math.dist(p, at)
            if best is None or d < best[0]:
                best = (d, i, p)
        return best[1], best[2]

    # checks

    def check(self) -> list[str]:
        self.layout()
        problems: list[str] = []
        shapes = [e for e in self._shapes() if not e.get("id", "").startswith("legend_")]
        texts = self._free_texts()
        wires = [self.by_id[w["id"]] for w in self.wires]
        labels = [self.by_id[f"{w['id']}__label"] for w in wires if f"{w['id']}__label" in self.by_id]
        rect = self.bounds

        def owner(e: dict) -> str | None:
            return e.get("_owner") or (e["groupIds"][-1] if e.get("groupIds") else None)

        for wid in self._stuck:
            w = next(x for x in self.wires if x["id"] == wid)
            problems.append(f"wire {wid} found no clear path from {w['src']} to {w['dst']}, open space or free its sides")
        for i, a in enumerate(shapes):
            for b in shapes[i + 1:]:
                ra, rb = rect(a["id"]), rect(b["id"])
                if route.overlap_area(ra, rb) > 0:
                    problems.append(f"{a['id']} and {b['id']} overlap")
                elif route.overlap_area(route.inflate(ra, MIN_GAP / 2), route.inflate(rb, MIN_GAP / 2)) > 0:
                    problems.append(f"{a['id']} and {b['id']} are closer than {MIN_GAP}px")

        for e in self.elements:
            parent = self.by_id.get(e.get("containerId") or "")
            if e["type"] != "text" or not parent or parent["type"] == "arrow":
                continue
            w, h = measure(e["text"], e["fontSize"], e["fontFamily"])
            factor = {"ellipse": math.sqrt(2) / 2, "diamond": 0.5}.get(parent["type"], 1.0)
            room_w = parent["width"] * factor - 2 * PAD - 4
            room_h = parent["height"] * factor - 2 * PAD - (3 * CAP if parent.get("_cylinder") else 0)
            if w > room_w or h > room_h:
                problems.append(f"label of {parent['id']} needs {w:.0f}x{h:.0f} but has {room_w:.0f}x{room_h:.0f}")

        zones = [e for e in self.elements if e.get("_zone")]
        for t in texts:
            rt = rect(t["id"])
            for s in shapes:
                if owner(t) in (s["id"], owner(s)) or (t["id"].startswith("legend_")):
                    continue
                if route.overlap_area(rt, rect(s["id"])) > 0:
                    problems.append(f"text {t['id']} runs into {s['id']}")
            for u in texts:
                if u is not t and t["id"] < u["id"] and route.overlap_area(rt, rect(u["id"])) > 0:
                    problems.append(f"text {t['id']} and {u['id']} overlap")
            for wire in wires:
                if any(route.seg_hits_rect(a, b, rt) for a, b in route.segments(self._points(wire["id"]))):
                    problems.append(f"wire {wire['id']} runs through text {t['id']}")
            for line in (e for e in self.elements if e["type"] == "line" and not e.get("_owner")):
                if any(route.seg_hits_rect(a, b, rt, 1) for a, b in route.segments(self._points(line["id"]))):
                    problems.append(f"line {line['id']} runs through text {t['id']}")
            for z in zones:
                rz = rect(z["id"])
                inside = rz[0] <= rt[0] and rz[1] <= rt[1] and rt[2] <= rz[2] and rt[3] <= rz[3]
                if not inside and route.overlap_area(rt, rz) > 0 and owner(t) != z["id"]:
                    problems.append(f"text {t['id']} sits on the border of zone {z['id']}")

        for z in zones:
            rz = rect(z["id"])
            for s in shapes:
                rs = rect(s["id"])
                inside = rz[0] <= rs[0] and rz[1] <= rs[1] and rs[2] <= rz[2] and rs[3] <= rz[3]
                if not inside and route.overlap_area(rs, rz) > 0:
                    problems.append(f"{s['id']} straddles the border of zone {z['id']}")

        ends = []
        for wire in wires:
            pts = self._points(wire["id"])
            segs = route.segments(pts)
            bound = {(wire.get("startBinding") or {}).get("elementId"), (wire.get("endBinding") or {}).get("elementId")}
            for s in shapes:
                if s["id"] in bound:
                    continue
                if any(route.seg_hits_rect(a, b, rect(s["id"]), 2) for a, b in segs):
                    problems.append(f"wire {wire['id']} passes through {s['id']}")
            for key, p in (("startBinding", pts[0]), ("endBinding", pts[-1])):
                ref = wire.get(key)
                if not ref:
                    continue
                x0, y0, x1, y1 = rect(ref["elementId"])
                if x0 + 2 < p[0] < x1 - 2 and y0 + 2 < p[1] < y1 - 2 and self.by_id[ref["elementId"]]["type"] == "rectangle":
                    problems.append(f"wire {wire['id']} stops inside {ref['elementId']}")
                ends.append((wire["id"], p))
            if wire["endArrowhead"] and segs and math.dist(*segs[-1]) < 30:
                problems.append(f"arrowhead of {wire['id']} is squeezed, give its last run 30px or more")
        for i, (a, pa) in enumerate(ends):
            for b, pb in ends[i + 1:]:
                if a != b and math.dist(pa, pb) < 8:
                    problems.append(f"wires {a} and {b} meet the same point")

        crossings = []
        for i, a in enumerate(wires):
            sa = route.segments(self._points(a["id"]))
            for b in wires[i + 1:]:
                sb = route.segments(self._points(b["id"]))
                shared = sum(route.shared_length(x, y, 4) for x in sa for y in sb)
                if shared > 12:
                    problems.append(f"wires {a['id']} and {b['id']} share a track for {shared:.0f}px")
                if any(route.crosses(x, y) for x in sa for y in sb):
                    crossings.append(f"{a['id']} and {b['id']}")

        for lab in labels:
            rl = rect(lab["id"])
            wire = self.by_id[lab["containerId"]]
            if lab.get("_cramped"):
                problems.append(f"label of {wire['id']} has no straight run long enough, shorten it or add space")
            limit = max(0.7 * max(wire["width"], wire["height"]), 11 * lab["fontSize"])
            if lab["width"] > limit:
                problems.append(f"label of {wire['id']} will wrap in the editor, keep it under {limit:.0f}px")
            for s in shapes:
                if route.overlap_area(rl, rect(s["id"])) > 0:
                    problems.append(f"label of {wire['id']} covers {s['id']}")
            for t in texts:
                if route.overlap_area(rl, rect(t["id"])) > 0:
                    problems.append(f"label of {wire['id']} covers text {t['id']}")
            for other in labels:
                if other["id"] > lab["id"] and route.overlap_area(rl, rect(other["id"])) > 0:
                    problems.append(f"labels of {wire['id']} and {other['containerId']} overlap")
            for z in zones:
                x0, y0, x1, y1 = rect(z["id"])
                edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1))]
                if any(route.seg_hits_rect(a, b, rl) for a, b in edges):
                    problems.append(f"label of {wire['id']} sits on the border of zone {z['id']}")
            for o in wires:
                if o is wire:
                    continue
                if any(route.seg_hits_rect(a, b, rl) for a, b in route.segments(self._points(o["id"]))):
                    problems.append(f"label of {wire['id']} hides part of {o['id']}")

        for fid, rf in self._frame_names():
            for e in shapes + texts:
                if route.overlap_area(rf, rect(e["id"])) > 0:
                    problems.append(f"name of frame {fid} runs into {e['id']}")

        for pair in crossings:
            problems.append(f"wires {pair} cross, reorder boxes with arrange() or move one so they sit side by side")
        return list(dict.fromkeys(problems))

    def save(self, path: str | Path) -> Path:
        self.layout()
        self.problems_found = self.check()
        for problem in self.problems_found:
            print(f"check {problem}", file=sys.stderr)
        frames = [e for e in self.elements if e["type"] == "frame"]
        out = []
        for e in self.elements:
            clean = {k: v for k, v in e.items() if not k.startswith("_")}
            if e["type"] != "frame":
                r = self.bounds(e["id"])
                for f in frames:
                    rf = self.bounds(f["id"])
                    if rf[0] <= r[0] and rf[1] <= r[1] and r[2] <= rf[2] and r[3] <= rf[3]:
                        clean["frameId"] = f["id"]
            out.append(clean)
        doc = {"type": "excalidraw", "version": 2, "source": "excalidraw-as-code", "elements": out,
               "appState": {"viewBackgroundColor": self.background, "gridSize": None}, "files": {}}
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(f"wrote {path}")
        return path
