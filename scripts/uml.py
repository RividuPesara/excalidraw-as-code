from __future__ import annotations

import math

from excalidraw import Scene

INK = "#1e1e1e"
WHITE = "#ffffff"
SIDES = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}


def _rect(s: Scene, id_: str, x: float, y: float, w: float, h: float, stroke: str = INK, bg: str = WHITE,
          width: float = 2, **kw) -> dict:
    return s._add(id_, "rectangle", x, y, w, h, stroke, bg, strokeWidth=width, **kw)


def _line(s: Scene, id_: str, pts: list, owner: str, width: float = 2, curve: bool = False,
          dashed: bool = False) -> dict:
    e = s.line(id_, pts, "dashed" if dashed else "solid", INK, width=width)
    e["_owner"] = owner
    if curve:
        e["roundness"] = {"type": 2}
    return e


def _icon(s: Scene, owner: str, x: float, y: float) -> None:
    # uml component glyph
    _rect(s, f"{owner}__ic", x + 2, y, 12, 15, width=1, _owner=owner)
    _rect(s, f"{owner}__ic1", x - 2, y + 3, 8, 4, width=1, _owner=owner)
    _rect(s, f"{owner}__ic2", x - 2, y + 9, 8, 4, width=1, _owner=owner)


def _stereo(name: str, stereo: str | None) -> str:
    return f"«{stereo}»\n{name}" if stereo else name


def component(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, stereo: str | None = None,
              size: float = 15, icon: bool = True) -> dict:
    e = _rect(s, id_, x, y, w, h, _shape=True)
    s._label(id_, _stereo(name, stereo), size, INK)
    if icon:
        _icon(s, id_, x + w - 18, y + 4)
    return e


def subsystem(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, size: float = 16,
              header: float = 34, icon: bool = True) -> dict:
    e = _rect(s, id_, x, y, w, h, _zone=True)
    s.text(f"{id_}__title", x + w / 2, y + (header - size * 1.15) / 2, name, size, INK, "center", _owner=id_)
    _line(s, f"{id_}__sep", [(x, y + header), (x + w, y + header)], id_, 1)
    if icon:
        _icon(s, id_, x + w - 26, y + 7)
    return e


def package(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, size: float = 15) -> dict:
    _rect(s, f"{id_}__tab", x, y - 12, min(48, w / 3), 12, _owner=id_)
    e = _rect(s, id_, x, y, w, h, _shape=True)
    s._label(id_, name, size, INK)
    return e


def layer(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, size: float = 17,
          model: bool = False) -> dict:
    # the triangle in the tab marks a model
    tw = s.text(f"{id_}__title", x + 10, y - 34 + (34 - size * 1.15) / 2, name, size, INK, _owner=id_)["width"]
    tab = tw + (46 if model else 22)
    _rect(s, f"{id_}__tab", x, y - 34, tab, 34, _owner=id_, before=f"{id_}__title")
    if model:
        tx = x + tab - 30
        _line(s, f"{id_}__tri", [(tx, y - 9), (tx + 10, y - 26), (tx + 20, y - 9), (tx, y - 9)], id_, 1.5)
    return _rect(s, id_, x, y, w, h, bg="transparent", _zone=True)


def node(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, stereo: str | None = "device",
         size: float = 15, depth: float = 12, holds: bool = True) -> dict:
    # holds=False gives a leaf that wires bind to
    _line(s, f"{id_}__top", [(x, y), (x + depth, y - depth), (x + w + depth, y - depth),
                             (x + w + depth, y + h - depth), (x + w, y + h)], id_)
    _line(s, f"{id_}__edge", [(x + w, y), (x + w + depth, y - depth)], id_)
    if holds:
        e = _rect(s, id_, x, y, w, h, _zone=True, _extent=(0, depth, depth, 0))
        s.text(f"{id_}__title", x + w / 2, y + 8, _stereo(name, stereo), size, INK, "center", _owner=id_)
        return e
    e = _rect(s, id_, x, y, w, h, _shape=True, _extent=(0, depth, depth, 0))
    s._label(id_, _stereo(name, stereo), size, INK)
    return e


def artifact(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, stereo: str | None = "artifact",
             size: float = 14) -> dict:
    e = _rect(s, id_, x, y, w, h, _shape=True)
    s._label(id_, _stereo(name, stereo), size, INK)
    ix, iy = x + w - 22, y + 6
    _line(s, f"{id_}__doc", [(ix, iy), (ix + 9, iy), (ix + 14, iy + 5), (ix + 14, iy + 18), (ix, iy + 18), (ix, iy)],
          id_, 1)
    _line(s, f"{id_}__fold", [(ix + 9, iy), (ix + 9, iy + 5), (ix + 14, iy + 5)], id_, 1)
    return e


def store(s: Scene, id_: str, x: float, y: float, w: float, h: float, name: str, size: float = 14) -> dict:
    e = s.box(id_, x, y, w, h, name, "plain", shape="cylinder", size=size)
    for o in s.elements:
        if o.get("_owner") == id_ and o["type"] != "text":
            o["backgroundColor"] = WHITE
            if o["strokeColor"] != "transparent":
                o["strokeColor"] = INK
    s.by_id[f"{id_}__label"]["strokeColor"] = INK
    return e


def _port(s: Scene, id_: str, owner: str, side: str, t: float, length: float) -> tuple:
    px, py = s.anchor(owner, side, t)
    dx, dy = SIDES[side]
    _rect(s, f"{id_}__port", px - 6, py - 6, 12, 12, _owner=id_)
    ex, ey = px + dx * length, py + dy * length
    _line(s, f"{id_}__stub", [(px + dx * 6, py + dy * 6), (ex, ey)], id_)
    return ex, ey, dx, dy


def _name(s: Scene, id_: str, cx: float, cy: float, side: str, name: str | None, r: float, size: float) -> None:
    if not name:
        return
    if side in ("left", "right"):
        s.text(f"{id_}__name", cx, cy - r - size * 1.15 - 2, name, size, INK, "center", _owner=id_)
    else:
        s.text(f"{id_}__name", cx + r + 4, cy - size * 0.6, name, size, INK, _owner=id_)


def provided(s: Scene, id_: str, owner: str, side: str, name: str | None = None, t: float = 0.5,
             length: float = 34, size: float = 15) -> dict:
    ex, ey, dx, dy = _port(s, id_, owner, side, t, length)
    r = 9
    bx, by = ex + dx * r, ey + dy * r
    ball = s._add(id_, "ellipse", bx - r, by - r, 2 * r, 2 * r, INK, WHITE, _shape=True, roundness={"type": 2})
    _name(s, id_, bx, by, side, name, r, size)
    return ball


def required(s: Scene, id_: str, owner: str, side: str, name: str | None = None, t: float = 0.5,
             length: float = 34, size: float = 15) -> dict:
    ex, ey, dx, dy = _port(s, id_, owner, side, t, length)
    r = 12
    cx, cy = ex + dx * r, ey + dy * r
    pts = []
    for k in range(7):
        a = math.pi / 2 + math.pi * k / 6
        ox, oy = r * math.cos(a), r * math.sin(a)
        pts.append({"left": (cx - ox, cy + oy), "right": (cx + ox, cy + oy), "top": (cx + oy, cy - ox),
                    "bottom": (cx + oy, cy + ox)}[side])
    _line(s, f"{id_}__arc", pts, id_, curve=True)
    # the socket is open so an invisible box in its middle takes the wire
    hit = _rect(s, id_, cx - 5, cy - 5, 10, 10, "transparent", "transparent", 0, _shape=True)
    _name(s, id_, cx, cy, side, name, r, size)
    return hit


def assembly(s: Scene, id_: str, consumer: str, provider: str, name: str | None = None, size: float = 15) -> None:
    # a routed wire cannot join shapes this small so the ball sits in the socket
    a, b = s.bounds(consumer), s.bounds(provider)
    across = b[0] >= a[2] or a[0] >= b[2]
    k = 0 if across else 1
    flip = a[k] > b[k]
    side_a = ("left" if flip else "right") if across else ("top" if flip else "bottom")
    side_b = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}[side_a]
    lo, hi = max(a[1 - k], b[1 - k]), min(a[3 - k], b[3 - k])
    if hi - lo < 12:
        raise ValueError(f"assembly {id_} needs {consumer} and {provider} to face each other")
    c = (lo + hi) / 2
    edge_a, edge_b = (a[k] if flip else a[k + 2]), (b[k + 2] if flip else b[k])
    mid = (edge_a + edge_b) / 2
    if abs(edge_b - edge_a) < 70:
        raise ValueError(f"assembly {id_} needs 70px or more between {consumer} and {provider}")
    ta = (c - a[1 - k]) / (a[3 - k] - a[1 - k])
    tb = (c - b[1 - k]) / (b[3 - k] - b[1 - k])
    # the ball sits inside the socket so only the ball stays a shape that wires bind to
    required(s, f"{id_}__req", consumer, side_a, None, ta, abs(mid - edge_a) - 12).pop("_shape")
    provided(s, id_, provider, side_b, name, tb, abs(edge_b - mid) - 9, size)


def frame(s: Scene, id_: str, x: float, y: float, w: float, h: float, kind: str, name: str, size: float = 16) -> dict:
    label = f"{kind} {name}"
    s.text(f"{id_}__title", x + 10, y + 6, label, size, INK, _owner=id_)
    tw = s.by_id[f"{id_}__title"]["width"] + 30
    _line(s, f"{id_}__tag", [(x, y + 30), (x + tw - 12, y + 30), (x + tw, y + 18), (x + tw, y)], id_, 1.5)
    return _rect(s, id_, x, y, w, h, bg="transparent", _zone=True, before=f"{id_}__title")


def titles_on_top(s: Scene) -> None:
    # hand routed wires would hide container names so names go last
    names = [e for e in s.elements if e["type"] == "text" and e["id"].endswith("__title")]
    for e in names:
        s.elements.remove(e)
    s.elements.extend(names)
