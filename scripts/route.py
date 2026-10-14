from __future__ import annotations

import heapq
import math

Rect = tuple[float, float, float, float]
Point = tuple[float, float]
Segment = tuple[Point, Point]

NORMAL = {"left": (-1, 0), "right": (1, 0), "top": (0, -1), "bottom": (0, 1)}
SIDES = tuple(NORMAL)

BEND = 60
CROSS = 350
SHARE = 600
HUG = 120


def inflate(r: Rect, m: float) -> Rect:
    return r[0] - m, r[1] - m, r[2] + m, r[3] + m


def overlap_area(a: Rect, b: Rect) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def seg_hits_rect(a: Point, b: Point, r: Rect, inset: float = 0) -> bool:
    x0, y0, x1, y1 = r[0] + inset, r[1] + inset, r[2] - inset, r[3] - inset
    if x0 >= x1 or y0 >= y1:
        return False
    # liang barsky clip against the open rectangle
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q <= 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return t1 - t0 > 1e-9


def segments(points: list[Point]) -> list[Segment]:
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def is_h(s: Segment) -> bool:
    return abs(s[0][1] - s[1][1]) < 0.5


def is_v(s: Segment) -> bool:
    return abs(s[0][0] - s[1][0]) < 0.5


def shared_length(a: Segment, b: Segment, tol: float = 6) -> float:
    if is_h(a) and is_h(b) and abs(a[0][1] - b[0][1]) < tol:
        lo, hi = max(min(a[0][0], a[1][0]), min(b[0][0], b[1][0])), min(max(a[0][0], a[1][0]), max(b[0][0], b[1][0]))
        return max(0.0, hi - lo)
    if is_v(a) and is_v(b) and abs(a[0][0] - b[0][0]) < tol:
        lo, hi = max(min(a[0][1], a[1][1]), min(b[0][1], b[1][1])), min(max(a[0][1], a[1][1]), max(b[0][1], b[1][1]))
        return max(0.0, hi - lo)
    return 0.0


def crosses(a: Segment, b: Segment) -> bool:
    (ax, ay), (bx, by) = a
    (cx, cy), (dx, dy) = b

    def orient(px, py, qx, qy, rx, ry):
        v = (qx - px) * (ry - py) - (qy - py) * (rx - px)
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)

    o1, o2 = orient(ax, ay, bx, by, cx, cy), orient(ax, ay, bx, by, dx, dy)
    o3, o4 = orient(cx, cy, dx, dy, ax, ay), orient(cx, cy, dx, dy, bx, by)
    return o1 * o2 < 0 and o3 * o4 < 0


def simplify(points: list[Point]) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if out and abs(out[-1][0] - p[0]) < 0.5 and abs(out[-1][1] - p[1]) < 0.5:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (abs(a[0] - b[0]) < 0.5 and abs(b[0] - p[0]) < 0.5) or (abs(a[1] - b[1]) < 0.5 and abs(b[1] - p[1]) < 0.5):
                out[-1] = p
                continue
        out.append(p)
    return out


def outline_point(rect: Rect, shape: str, side: str, t: float) -> Point:
    x0, y0, x1, y1 = rect
    cx, cy, a, b = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    if side in ("top", "bottom"):
        x = x0 + (x1 - x0) * t
        u = min(1.0, abs(x - cx) / a) if a else 0.0
        reach = b if shape == "rectangle" else (b * math.sqrt(1 - u * u) if shape == "ellipse" else b * (1 - u))
        return x, cy - reach if side == "top" else cy + reach
    y = y0 + (y1 - y0) * t
    u = min(1.0, abs(y - cy) / b) if b else 0.0
    reach = a if shape == "rectangle" else (a * math.sqrt(1 - u * u) if shape == "ellipse" else a * (1 - u))
    return (cx - reach if side == "left" else cx + reach), y


def side_point(rect: Rect, side: str, t: float, out: float = 0) -> Point:
    x0, y0, x1, y1 = rect
    nx, ny = NORMAL[side]
    if side in ("top", "bottom"):
        return x0 + (x1 - x0) * t, (y0 if side == "top" else y1) + ny * out
    return (x0 if side == "left" else x1) + nx * out, y0 + (y1 - y0) * t


def facing(src: Rect, dst: Rect) -> dict[str, float]:
    # how badly each side of src points away from dst
    sx, sy = (src[0] + src[2]) / 2, (src[1] + src[3]) / 2
    dx, dy = (dst[0] + dst[2]) / 2, (dst[1] + dst[3]) / 2
    gaps = {"right": dst[0] - src[2], "left": src[0] - dst[2], "bottom": dst[1] - src[3], "top": src[1] - dst[3]}
    out = {}
    for side, (nx, ny) in NORMAL.items():
        along = (dx - sx) * nx + (dy - sy) * ny
        out[side] = 0 if gaps[side] > 0 else (BEND if along > 0 else 3 * BEND)
    return out


class Router:
    def __init__(self, obstacles: list[Rect], margin: float = 14) -> None:
        self.obstacles = obstacles
        self.margin = margin
        self.taken: list[Segment] = []
        self.soft: list[Segment] = []

    def route(self, src: Rect, dst: Rect, starts: dict[str, Point], ends: dict[str, Point],
              start_cost: dict[str, float], end_cost: dict[str, float], stub_out: float, stub_in: float,
              skip: tuple[int, ...] = ()) -> list[Point] | None:
        m = self.margin
        blocks = [inflate(r, m) for i, r in enumerate(self.obstacles) if i not in skip]
        blocks += [inflate(src, 2), inflate(dst, 2)]
        stubs_s = {s: self._stub(p, s, stub_out) for s, p in starts.items()}
        stubs_d = {s: self._stub(p, s, stub_in) for s, p in ends.items()}
        xs, ys = set(), set()
        for p in list(stubs_s.values()) + list(stubs_d.values()):
            xs.add(p[0])
            ys.add(p[1])
        edges_x, edges_y = [], []
        for r in blocks:
            xs.update((r[0], r[2]))
            ys.update((r[1], r[3]))
            edges_x += [r[0], r[2]]
            edges_y += [r[1], r[3]]
        # channel centres keep wires in the middle of the gaps between shapes
        for edges, axis in ((sorted(set(edges_x)), xs), (sorted(set(edges_y)), ys)):
            for a, b in zip(edges, edges[1:]):
                if b - a > 2 * m:
                    axis.add((a + b) / 2)
        lo_x = min(xs) - 60
        hi_x = max(xs) + 60
        lo_y = min(ys) - 60
        hi_y = max(ys) + 60
        xs.update((lo_x, hi_x))
        ys.update((lo_y, hi_y))
        X, Y = sorted(xs), sorted(ys)

        def inside(p: Point) -> bool:
            return any(r[0] < p[0] < r[2] and r[1] < p[1] < r[3] for r in blocks)

        def blocked(a: Point, b: Point, among: list[Rect] = blocks) -> bool:
            return any(seg_hits_rect(a, b, r) for r in among)

        goal = {(X.index(p[0]), Y.index(p[1])): s for s, p in stubs_d.items()}

        def h(ix: int, iy: int) -> float:
            return min(abs(X[ix] - X[gx]) + abs(Y[iy] - Y[gy]) for gx, gy in goal)

        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        heap: list = []
        best: dict = {}
        for s, p in stubs_s.items():
            if inside(p) or blocked(starts[s], p, blocks[:-2]):
                continue
            node = (X.index(p[0]), Y.index(p[1]), dirs.index(NORMAL[s]))
            g = start_cost.get(s, 0)
            best[node] = (g, None, s)
            heapq.heappush(heap, (g + h(node[0], node[1]), g, node))
        found = None
        edge_cache: dict = {}
        while heap:
            f, g, node = heapq.heappop(heap)
            if best.get(node, (math.inf,))[0] < g:
                continue
            ix, iy, d = node
            if (ix, iy) in goal:
                side = goal[(ix, iy)]
                inward = dirs.index((-NORMAL[side][0], -NORMAL[side][1]))
                total = g + (0 if d == inward else BEND) + end_cost.get(side, 0)
                if dirs[d] != NORMAL[side] and (found is None or total < found[0]):
                    found = (total, node, side)
            if found and f >= found[0]:
                break
            for nd, (ddx, ddy) in enumerate(dirs):
                if nd != d and dirs[d] == (-ddx, -ddy):
                    continue
                jx, jy = ix + ddx, iy + ddy
                if not (0 <= jx < len(X) and 0 <= jy < len(Y)):
                    continue
                a, b = (X[ix], Y[iy]), (X[jx], Y[jy])
                key = (ix, iy, jx, jy)
                if key not in edge_cache:
                    edge_cache[key] = inside(b) or blocked(a, b)
                if edge_cache[key]:
                    continue
                cost = abs(b[0] - a[0]) + abs(b[1] - a[1]) + (BEND if nd != d else 0) + self._penalty((a, b))
                nxt = (jx, jy, nd)
                ng = g + cost
                if ng < best.get(nxt, (math.inf,))[0]:
                    best[nxt] = (ng, node, None)
                    heapq.heappush(heap, (ng + h(jx, jy), ng, nxt))
        if not found:
            return None
        _, node, side_d = found
        path = []
        while node is not None:
            path.append((X[node[0]], Y[node[1]]))
            g, prev, side_s = best[node]
            if prev is None:
                start_side = side_s
            node = prev
        path.reverse()
        return simplify([starts[start_side]] + path + [ends[side_d]])

    def _stub(self, p: Point, side: str, length: float) -> Point:
        nx, ny = NORMAL[side]
        return p[0] + nx * length, p[1] + ny * length

    def _penalty(self, seg: Segment) -> float:
        cost = 0.0
        for t in self.taken:
            shared = shared_length(seg, t)
            if shared:
                cost += SHARE + 4 * shared
            elif crosses(seg, t):
                cost += CROSS
        for t in self.soft:
            shared = shared_length(seg, t, 8)
            if shared:
                cost += HUG + shared
        return cost

    def commit(self, points: list[Point]) -> None:
        self.taken += segments(points)


def place_label(points: list[Point], w: float, h: float, obstacles: list[Rect], wires: list[Segment],
                borders: list[Segment], head_end: bool, head_start: bool) -> tuple[int, Point, float]:
    best = None
    segs = segments(points)
    longest = max(math.dist(a, b) for a, b in segs)
    for i, (a, b) in enumerate(segs):
        length = math.dist(a, b)
        if length < 1:
            continue
        along = w if is_h((a, b)) else h
        lo = 30 if (i == 0 and head_start) else 10
        hi = 30 if (i == len(segs) - 1 and head_end) else 10
        room = length - lo - hi
        for t in (0.5, 0.4, 0.6, 0.3, 0.7):
            d = lo + room * t if room > 0 else length / 2
            p = (a[0] + (b[0] - a[0]) * d / length, a[1] + (b[1] - a[1]) * d / length)
            box = (p[0] - w / 2 - 4, p[1] - h / 2 - 2, p[0] + w / 2 + 4, p[1] + h / 2 + 2)
            # centred on the longest run reads best
            score = abs(t - 0.5) * 30 + (1 - length / longest) * 60
            if room < along + 8:
                score += 2000 + (along + 8 - room) * 10
            for r in obstacles:
                score += overlap_area(box, r) * 4
            for s in wires:
                if seg_hits_rect(s[0], s[1], box):
                    score += 900
            for s in borders:
                if seg_hits_rect(s[0], s[1], inflate(box, 3)):
                    score += 900
            if best is None or score < best[0]:
                best = (score, i, p)
    return best[1], best[2], best[0]


def center_label(points: list[Point], seg: int, p: Point, half: float) -> tuple[list[Point], float]:
    # excalidraw and kroki draw a wire label on the middle point so make p the middle point
    pts = points[:seg + 1] + [p] + points[seg + 1:]
    k = seg + 1
    before, after = k, len(pts) - 1 - k
    if before != after:
        n = abs(before - after)
        q = pts[k - 1] if before < after else pts[k + 1]
        length = math.dist(p, q)
        # extra points sit on the label segment just clear of the label so the wire looks the same
        start = half + 6 if length > half + 12 + 2 * n else 0.0
        extra = []
        for j in range(n):
            # packed against the label so the run into an arrowhead keeps its length
            d = start + 2 * (j + 1) if start else length * (j + 1) / (n + 1)
            extra.append((p[0] + (q[0] - p[0]) * d / length, p[1] + (q[1] - p[1]) * d / length))
        if before < after:
            pts = pts[:k] + list(reversed(extra)) + pts[k:]
        else:
            pts = pts[:k + 1] + extra + pts[k + 1:]
    total = sum(math.dist(a, b) for a, b in segments(pts))
    upto = sum(math.dist(a, b) for a, b in segments(pts[:len(pts) // 2 + 1]))
    return pts, (upto / total if total else 0.5)

