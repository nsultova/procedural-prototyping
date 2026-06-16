"""Slime Mould — a branching vein network grown by space colonization.

Space-colonization growth (Runions et al.): scatter "food" attractor points,
grow a tree from a root in one corner toward them, consuming food as branches
reach it. Branch thickness is derived from subtree size (Da Vinci rule), giving
thick trunk arteries that taper to hair-thin tips, with dense fan-fronts forming
naturally at the advancing growth edge.

Pure: params + rng -> list[Path] (open polylines, each carrying a tapered width).
"""

import math

from engine.types import Path, Canvas


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    n_attr = int(p["num_attractors"])
    infl = p["influence_radius"]
    kill = p["kill_radius"]
    step = p["step_size"]
    max_steps = int(p["max_steps"])
    frontier_bias = p["frontier_bias"]
    wander = p["wander"]
    min_w = p["min_width"]
    max_w = p["max_width"]
    w_exp = max(p["width_exponent"], 1e-6)
    fan_density = int(p["fan_density"])
    fan_length = p["fan_length"]
    fan_spread = p["fan_spread"]
    fan_depth = int(p["fan_depth"])
    distortion = p["distortion"]
    distortion_scale = p["distortion_scale"]
    bubble_density = int(p["bubble_density"])
    bubble_size = p["bubble_size"]

    # Root in the lower-left corner; growth heads toward the top-right frontier.
    root = (0.05 * W, 0.95 * H)
    max_d = math.hypot(W, H)

    # --- scatter food, optionally biased away from the root toward the frontier
    attractors = []
    for _ in range(n_attr):
        x = rng.random() * W
        y = rng.random() * H
        if frontier_bias > 0:
            for _a in range(8):  # rejection-sample toward far-from-root
                dn = math.hypot(x - root[0], y - root[1]) / max_d
                if rng.random() <= dn ** frontier_bias:
                    break
                x = rng.random() * W
                y = rng.random() * H
        attractors.append((x, y))

    nodes = [root]
    parents = [-1]

    # spatial hash of node indices (cell = influence radius) for fast nearest()
    cell = max(infl, 1e-6)
    grid = {}

    def grid_add(i):
        nx, ny = nodes[i]
        grid.setdefault((int(nx // cell), int(ny // cell)), []).append(i)

    grid_add(0)

    def nearest_within(x, y):
        """Nearest node within `infl`; (-1, infl) if none. Uses the 3x3 cells."""
        cx, cy = int(x // cell), int(y // cell)
        best_i, best_d = -1, infl
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for i in grid.get((gx, gy), ()):
                    nx, ny = nodes[i]
                    d = math.hypot(x - nx, y - ny)
                    if d < best_d:
                        best_d, best_i = d, i
        return best_i, best_d

    def grow(ni, ux, uy):
        if wander > 0:
            ang = (rng.random() - 0.5) * wander * math.pi
            ca, sa = math.cos(ang), math.sin(ang)
            ux, uy = ux * ca - uy * sa, ux * sa + uy * ca
        nx = min(max(nodes[ni][0] + ux * step, 0.0), W)
        ny = min(max(nodes[ni][1] + uy * step, 0.0), H)
        nodes.append((nx, ny))
        parents.append(ni)
        grid_add(len(nodes) - 1)

    active = attractors
    for _ in range(max_steps):
        if not active:
            break
        pulls = {}          # node index -> [sum dx, sum dy] of unit pull dirs
        survivors = []
        for (ax, ay) in active:
            ni, d = nearest_within(ax, ay)
            if ni < 0:
                survivors.append((ax, ay))   # nothing close enough yet — wait
                continue
            if d <= kill:
                continue                     # reached — consume this food
            survivors.append((ax, ay))
            nx, ny = nodes[ni]
            inv = 1.0 / d
            acc = pulls.get(ni)
            if acc is None:
                pulls[ni] = [(ax - nx) * inv, (ay - ny) * inv]
            else:
                acc[0] += (ax - nx) * inv
                acc[1] += (ay - ny) * inv
        active = survivors

        if pulls:
            for ni, (dx, dy) in pulls.items():
                mag = math.hypot(dx, dy)
                if mag < 1e-9:
                    continue
                grow(ni, dx / mag, dy / mag)
        elif active:
            # Bootstrap / bridge a gap: nothing is within influence, so extend
            # the single closest node toward the closest food (capped scan).
            best_d, best_ni, best_a = float("inf"), -1, None
            for (ax, ay) in active[:200]:
                for i in range(len(nodes)):
                    nxx, nyy = nodes[i]
                    d = math.hypot(ax - nxx, ay - nyy)
                    if d < best_d:
                        best_d, best_ni, best_a = d, i, (ax, ay)
            if best_ni < 0:
                break
            ax, ay = best_a
            nx, ny = nodes[best_ni]
            dd = best_d or 1.0
            grow(best_ni, (ax - nx) / dd, (ay - ny) / dd)
        else:
            break

    # --- branch thickness from subtree leaf count (parent index < child index)
    n = len(nodes)
    children = [[] for _ in range(n)]
    for i in range(1, n):
        children[parents[i]].append(i)
    leaves = [1 if not children[i] else 0 for i in range(n)]
    for i in range(n - 1, 0, -1):
        leaves[parents[i]] += leaves[i]
    total_leaves = max(leaves[0], 1)

    def width_of(i):
        norm = leaves[i] / total_leaves            # 1 at root, small at tips
        w = min_w + (max_w - min_w) * norm ** w_exp
        return max(min_w, min(max_w, w))

    # --- emit continuous strands as polylines (one per branch run) ---
    paths: list[Path] = []
    for c in range(1, n):
        par = parents[c]
        # a strand starts at every child of the root and every child of a fork
        if par != 0 and len(children[par]) == 1:
            continue
        poly = [nodes[par], nodes[c]]
        cur = c
        while len(children[cur]) == 1:
            cur = children[cur][0]
            poly.append(nodes[cur])
        if len(poly) >= 2:
            paths.append(Path(points=poly, width=width_of(c)))

    # --- optional fan-fronts: fuzzy tufts sprouting outward from each tip ---
    # All extra passes are skipped (no rng consumed) when their gate is 0, so
    # the baseline output is unchanged.
    if fan_density > 0:
        FAN_CAP = 12000
        made = 0
        for li in range(1, n):
            if children[li]:
                continue                       # only leaves (growth tips) bloom
            lx, ly = nodes[li]
            px, py = nodes[parents[li]]
            dx, dy = lx - px, ly - py
            dlen = math.hypot(dx, dy) or 1.0
            seeds = [(lx, ly, dx / dlen, dy / dlen, fan_length, fan_depth)]
            while seeds and made < FAN_CAP:
                sx, sy, ux, uy, length, depth = seeds.pop()
                twigs = fan_density if depth == fan_depth else 2
                for _t in range(twigs):
                    a = (rng.random() - 0.5) * fan_spread * math.pi
                    ca, sa = math.cos(a), math.sin(a)
                    tx, ty = ux * ca - uy * sa, ux * sa + uy * ca
                    L = length * (0.6 + 0.4 * rng.random())
                    mx = min(max(sx + tx * L * 0.5, 0.0), W)
                    my = min(max(sy + ty * L * 0.5, 0.0), H)
                    ex = min(max(sx + tx * L, 0.0), W)
                    ey = min(max(sy + ty * L, 0.0), H)
                    paths.append(Path(points=[(sx, sy), (mx, my), (ex, ey)], width=min_w))
                    made += 1
                    if depth > 1 and made < FAN_CAP:
                        seeds.append((ex, ey, tx, ty, length * 0.6, depth - 1))
                    if made >= FAN_CAP:
                        break

    # --- optional bubbles: little vacuole rings scattered on the network ---
    if bubble_density > 0 and n > 1:
        for _ in range(bubble_density):
            idx = 1 + int(rng.random() * (n - 1))
            bx, by = nodes[idx]
            r = bubble_size * (0.5 + rng.random())
            ring = [(bx + r * math.cos(2 * math.pi * k / 16),
                     by + r * math.sin(2 * math.pi * k / 16)) for k in range(16)]
            paths.append(Path(points=ring, closed=True, width=min_w))

    # --- optional distortion: perpendicular wobble on every polyline ---
    # Interior points only (endpoints stay put, so branch connections hold).
    if distortion > 0:
        freq = distortion_scale * 0.05
        wobbled = []
        for path in paths:
            pts = path.points
            if len(pts) < 3:
                wobbled.append(path)
                continue
            phase = rng.random() * 2.0 * math.pi
            s = 0.0
            out = [pts[0]]
            for i in range(1, len(pts) - 1):
                x0, y0 = pts[i - 1]
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                s += math.hypot(x1 - x0, y1 - y0)
                tx, ty = x2 - x0, y2 - y0
                tlen = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / tlen, tx / tlen
                off = distortion * math.sin(freq * s + phase)
                out.append((min(max(x1 + nx * off, 0.0), W),
                            min(max(y1 + ny * off, 0.0), H)))
            out.append(pts[-1])
            wobbled.append(Path(points=out, closed=path.closed, width=path.width))
        paths = wobbled

    return paths
