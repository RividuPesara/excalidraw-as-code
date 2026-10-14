from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = "https://github.com/excalidraw/excalidraw-libraries"
RAW = "https://raw.githubusercontent.com/excalidraw/excalidraw-libraries/main"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "excalidraw-as-code"
SKILL = Path(__file__).resolve().parent.parent

# types the kroki exporter cannot draw from a library item
DROP = {"frame", "magicframe", "image", "embeddable", "iframe"}


def root() -> Path | None:
    candidates = [os.environ.get("EXCALIDRAW_LIBRARIES"), SKILL.parent / "excalidraw-libraries",
                  CACHE / "excalidraw-libraries"]
    for c in candidates:
        if c and (Path(c) / "libraries.json").exists():
            return Path(c)
    return None


def _fetch(rel: str) -> Path:
    dest = CACHE / "raw" / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(f"{RAW}/{rel}", dest)
    return dest


def catalogue() -> list[dict]:
    base = root()
    path = base / "libraries.json" if base else _fetch("libraries.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load(source: str) -> dict:
    if Path(source).exists():
        return json.loads(Path(source).read_text(encoding="utf-8"))
    base = root()
    path = base / "libraries" / source if base else _fetch(f"libraries/{source}")
    return json.loads(path.read_text(encoding="utf-8"))


def items(lib: dict) -> list[tuple[str, list[dict]]]:
    out = []
    for i, it in enumerate(lib.get("libraryItems") or lib.get("library") or []):
        if isinstance(it, list):
            out.append((f"item{i}", it))
        else:
            out.append((it.get("name") or f"item{i}", it.get("elements", [])))
    return out


def pick(source: str, item: str | int) -> tuple[str, list[dict]]:
    all_items = items(load(source))
    if isinstance(item, int) or str(item).isdigit():
        return all_items[int(item)]
    for exact in (True, False):
        for name, els in all_items:
            if (name.lower() == str(item).lower()) if exact else (str(item).lower() in name.lower()):
                return name, els
    raise KeyError(f"no item {item!r} in {source}, run library.py items {source}")


def _bounds(e: dict) -> tuple[float, float, float, float]:
    x, y = e.get("x", 0), e.get("y", 0)
    pts = e.get("points")
    if pts:
        xs, ys = [x + p[0] for p in pts], [y + p[1] for p in pts]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    else:
        x0, y0, x1, y1 = x, y, x + e.get("width", 0), y + e.get("height", 0)
    a = e.get("angle") or 0
    if a:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        c, s = math.cos(a), math.sin(a)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        rx = [cx + (px - cx) * c - (py - cy) * s for px, py in corners]
        ry = [cy + (px - cx) * s + (py - cy) * c for px, py in corners]
        x0, x1, y0, y1 = min(rx), max(rx), min(ry), max(ry)
    return x0, y0, x1, y1


def usable(els: list[dict], keep_text: bool) -> list[dict]:
    keep = [e for e in els if e.get("type") not in DROP and not e.get("isDeleted")]
    if not keep_text:
        keep = [e for e in keep if e.get("type") != "text"]
    return keep


def place(els: list[dict], x: float, y: float, w: float, h: float, prefix: str,
          keep_text: bool = False) -> list[dict]:
    els = usable(els, keep_text)
    if not els:
        raise ValueError("library item has nothing the exporter can draw")
    b = [_bounds(e) for e in els]
    x0, y0 = min(r[0] for r in b), min(r[1] for r in b)
    bw, bh = max(r[2] for r in b) - x0, max(r[3] for r in b) - y0
    scale = min(w / bw if bw else 1, h / bh if bh else 1)
    # centre the icon inside the requested box
    ox, oy = x + (w - bw * scale) / 2, y + (h - bh * scale) / 2
    ids = {e["id"]: f"{prefix}_{e['id']}" for e in els if "id" in e}
    out = []
    for e in els:
        e = copy.deepcopy(e)
        for k in ("index", "versionNonce", "frameId"):
            e.pop(k, None)
        e["id"] = ids.get(e.get("id"), f"{prefix}_{len(out)}")
        e["x"] = (e.get("x", 0) - x0) * scale + ox
        e["y"] = (e.get("y", 0) - y0) * scale + oy
        for k in ("width", "height"):
            if k in e:
                e[k] *= scale
        if "points" in e:
            e["points"] = [[px * scale, py * scale] for px, py in e["points"]]
        if "fontSize" in e:
            e["fontSize"] *= scale
        e["groupIds"] = [f"{prefix}_{g}" for g in e.get("groupIds") or []] + [prefix]
        if e.get("containerId"):
            e["containerId"] = ids.get(e["containerId"])
        e["boundElements"] = [dict(be, id=ids[be["id"]]) for be in e.get("boundElements") or []
                              if be.get("id") in ids] or None
        for k in ("startBinding", "endBinding"):
            if e.get(k):
                e[k] = dict(e[k], elementId=ids[e[k]["elementId"]]) if e[k].get("elementId") in ids else None
        e["updated"] = 1
        out.append(e)
    return out


def index() -> list[tuple[str, str, int, str]]:
    base = root()
    if not base:
        return []
    cache = CACHE / "index.json"
    stamp = str((base / "libraries.json").stat().st_mtime)
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("stamp") == stamp:
            return [tuple(r) for r in data["rows"]]
    rows = []
    for lib in catalogue():
        try:
            for i, (name, _) in enumerate(items(load(lib["source"]))):
                rows.append((lib["source"], lib["name"], i, name))
        except (OSError, ValueError):
            continue
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"stamp": stamp, "rows": rows}), encoding="utf-8")
    return rows


def search(words: list[str]) -> None:
    words = [w.lower() for w in words]
    rows = index()
    if rows:
        named = [r for r in rows if all(w in f"{r[1]} {r[3]}".lower() for w in words)
                 and any(w in r[3].lower() for w in words)]
        for source, lib, i, name in named[:60]:
            print(f"{source} {i} {name}    ({lib})")
        libs: dict[str, int] = {}
        for r in rows:
            if all(w in f"{r[0]} {r[1]}".lower() for w in words) and r not in named:
                libs[r[0]] = libs.get(r[0], 0) + 1
        for source, n in libs.items():
            print(f"{source}    whole library matches, {n} items")
        print(f"{len(named)} items" + (", showing 60" if len(named) > 60 else ""))
        return
    print("no local clone so matching library names only, run library.py sync to search item names", file=sys.stderr)
    for lib in catalogue():
        if all(w in f"{lib['name']} {lib.get('description', '')}".lower() for w in words):
            print(f"{lib['source']}    {lib['name']}")


def sheet(source: str, out: Path, cols: int = 8, cell: int = 120) -> Path:
    elements = []
    for i, (name, els) in enumerate(items(load(source))):
        x, y = (i % cols) * (cell + 40), (i // cols) * (cell + 70)
        try:
            elements += place(els, x, y, cell, cell, f"i{i}", keep_text=True)
        except ValueError:
            pass
        caption = f"{i} {name}"[:22]
        elements.append({"id": f"cap{i}", "type": "text", "x": x, "y": y + cell + 8, "width": cell, "height": 18,
                         "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
                         "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0,
                         "opacity": 100, "groupIds": [], "roundness": None, "seed": 9000 + i, "version": 1,
                         "isDeleted": False, "boundElements": None, "updated": 1, "link": None, "locked": False,
                         "text": caption, "originalText": caption, "fontSize": 13, "fontFamily": 2,
                         "textAlign": "left", "verticalAlign": "top", "containerId": None, "lineHeight": 1.15})
    doc = {"type": "excalidraw", "version": 2, "source": "excalidraw-as-code", "elements": elements,
           "appState": {"viewBackgroundColor": "#ffffff"}, "files": {}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Find and preview excalidraw community library icons")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="find items by words in their name or library")
    s.add_argument("words", nargs="+")
    s = sub.add_parser("items", help="list the items of one library")
    s.add_argument("source")
    s = sub.add_parser("sheet", help="write a numbered contact sheet to render and look at")
    s.add_argument("source")
    s.add_argument("-o", "--out", type=Path)
    sub.add_parser("sync", help="clone the library repo into the cache for item search")
    sub.add_parser("where", help="print which library folder is in use")
    args = ap.parse_args()

    if args.cmd == "search":
        search(args.words)
    elif args.cmd == "items":
        for i, (name, els) in enumerate(items(load(args.source))):
            print(f"{i:4} {name}  ({len(usable(els, True))} elements)")
    elif args.cmd == "sheet":
        out = args.out or Path(args.source.replace("/", "_")).with_suffix(".excalidraw")
        print(f"wrote {sheet(args.source, out)}")
    elif args.cmd == "sync":
        dest = CACHE / "excalidraw-libraries"
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--depth", "1", REPO, str(dest)], check=True)
        print(f"libraries in {dest}")
    else:
        print(root() or f"none, items are fetched from {RAW} into {CACHE / 'raw'}")


if __name__ == "__main__":
    main()
