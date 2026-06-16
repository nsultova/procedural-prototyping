"""Slime Mould — a branching vein network grown by space colonization, with
hatched lobed fronds at the growth frontier and a thin reconnecting (mesh) layer.

Three layers, all pure (params + rng -> list[Path], deterministic):
  1. Veins   — space-colonization tree from a corner root; thickness from
               subtree size (Da Vinci), thick trunk tapering to fine tips.
  2. Mesh    — thin links between nearby, non-adjacent nodes, injecting loops
               -> enclosed cells/holes -> the reticulated organism interior.
  3. Fronds  — growth tips are clustered into lobes that bulge outward and are
               filled with a fading spray of short radial strokes: directional
               hatching that reads as the billowing fuzzy fan-fronts.

All output is open polylines; tone comes from stroke density.
"""

import math

from engine.types import Path, Canvas


def _mesh_links(nodes, parents, mesh_dist, mesh_density, width, rng):
    """Thin links between nearby non-adjacent nodes (loops -> cells)."""
    links = []
    cell = max(mesh_dist, 1e-6)
    grid = {}
    for i, (x, y) in enumerate(nodes):
        grid.setdefault((int(x // cell), int(y // cell)), []).append(i)
    cap = 4000
    for i, (x, y) in enumerate(nodes):
        cx, cy = int(x // cell), int(y // cell)
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for j in grid.get((gx, gy), ()):
                    if j <= i or parents[i] == j or parents[j] == i:
                        continue
                    nx, ny = nodes[j]
                    dist = math.hypot(x - nx, y - ny)
                    if dist > mesh_dist:
                        continue
                    if rng.random() >= mesh_density:
                        continue
                    # gentle sag so links read as organic cell-walls, not struts
                    mx, my = (x + nx) * 0.5, (y + ny) * 0.5
                    sag = (rng.random() - 0.5) * dist * 0.35
                    px, py = -(ny - y) / (dist or 1.0), (nx - x) / (dist or 1.0)
                    links.append(Path(points=[(x, y),
                                              (mx + px * sag, my + py * sag),
                                              (nx, ny)], width=width))
                    if len(links) >= cap:
                        return links
    return links


_FAN_SPREAD = 1.5  # radians; fronds comb outward in a fan, not a 360° starburst


def _frond_strokes(cx, cy, base, ux, uy, lobes, n_fill, stroke_len, width, rng, W, H):
    """A lobe bulging outward (ux,uy), filled with short curved hairs that comb
    outward — dense soft fur with a fading rim, not a spiky radial burst."""
    strokes = []
    da = math.atan2(uy, ux)
    p1 = rng.random() * 2.0 * math.pi
    p2 = rng.random() * 2.0 * math.pi

    def radius(th):
        wav = 1.0 + lobes * (0.6 * math.sin(3 * th + p1) + 0.4 * math.sin(5 * th + p2))
        bulge = 1.0 + 0.6 * max(0.0, math.cos(th - da))   # swell away from trunk
        return base * max(0.2, wav) * bulge

    for _ in range(n_fill):
        # place a hair somewhere in the lobe, biased outward and toward the core
        th = da + (rng.random() - 0.5) * 2.2          # mostly on the outward side
        rr = radius(th) * (rng.random() ** 0.7)
        px = cx + rr * math.cos(th)
        py = cy + rr * math.sin(th)
        # the hair itself combs outward (fan direction) with a little curl
        ang = da + (rng.random() - 0.5) * _FAN_SPREAD
        L = stroke_len * (0.5 + rng.random())
        ex, ey = px + math.cos(ang) * L, py + math.sin(ang) * L
        perp = ang + math.pi / 2
        curl = (rng.random() - 0.5) * L * 0.5
        mx = (px + ex) * 0.5 + math.cos(perp) * curl
        my = (py + ey) * 0.5 + math.sin(perp) * curl
        strokes.append(Path(points=[
            (min(max(px, 0.0), W), min(max(py, 0.0), H)),
            (min(max(mx, 0.0), W), min(max(my, 0.0), H)),
            (min(max(ex, 0.0), W), min(max(ey, 0.0), H)),
        ], width=width))
    return strokes


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
    frond_density = p["frond_density"]
    frond_size = max(p["frond_size"], 1e-6)
    frond_lobes = p["frond_lobes"]
    frond_fill = int(p["frond_fill"])
    frond_stroke = p["frond_stroke"]
    mesh_density = p["mesh_density"]
    mesh_dist = p["mesh_dist"]

    # Root in the lower-left corner; growth heads toward the top-right frontier.
    root = (0.05 * W, 0.95 * H)
    max_d = math.hypot(W, H)

    # --- scatter food, optionally biased away from the root toward the frontier
    attractors = []
    for _ in range(n_attr):
        x = rng.random() * W
        y = rng.random() * H
        if frontier_bias > 0:
            for _a in range(8):
                dn = math.hypot(x - root[0], y - root[1]) / max_d
                if rng.random() <= dn ** frontier_bias:
                    break
                x = rng.random() * W
                y = rng.random() * H
        attractors.append((x, y))

    nodes = [root]
    parents = [-1]

    cell = max(infl, 1e-6)
    grid = {}

    def grid_add(i):
        nx, ny = nodes[i]
        grid.setdefault((int(nx // cell), int(ny // cell)), []).append(i)

    grid_add(0)

    def nearest_within(x, y):
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
        pulls = {}
        survivors = []
        for (ax, ay) in active:
            ni, d = nearest_within(ax, ay)
            if ni < 0:
                survivors.append((ax, ay))
                continue
            if d <= kill:
                continue
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
        norm = leaves[i] / total_leaves
        w = min_w + (max_w - min_w) * norm ** w_exp
        return max(min_w, min(max_w, w))

    # --- veins: continuous strands as polylines ---
    paths: list[Path] = []
    for c in range(1, n):
        par = parents[c]
        if par != 0 and len(children[par]) == 1:
            continue
        poly = [nodes[par], nodes[c]]
        cur = c
        while len(children[cur]) == 1:
            cur = children[cur][0]
            poly.append(nodes[cur])
        if len(poly) >= 2:
            paths.append(Path(points=poly, width=width_of(c)))

    # --- mesh: thin reconnecting links (loops -> cells) ---
    if mesh_density > 0 and mesh_dist > 0:
        paths.extend(_mesh_links(nodes, parents, mesh_dist, mesh_density, min_w, rng))

    # --- fronds: hatched lobed masses at clustered growth tips ---
    if frond_density > 0 and frond_fill > 0 and n > 1:
        cells = {}  # grid key -> [count, sum_x, sum_y, sum_dx, sum_dy]
        for i in range(1, n):
            if children[i]:
                continue
            x, y = nodes[i]
            px, py = nodes[parents[i]]
            ddx, ddy = x - px, y - py
            dl = math.hypot(ddx, ddy) or 1.0
            key = (int(x // frond_size), int(y // frond_size))
            acc = cells.get(key)
            if acc is None:
                cells[key] = [1, x, y, ddx / dl, ddy / dl]
            else:
                acc[0] += 1; acc[1] += x; acc[2] += y
                acc[3] += ddx / dl; acc[4] += ddy / dl
        FROND_CAP = 9000
        for (cnt, sx, sy, sdx, sdy) in cells.values():
            cx, cy = sx / cnt, sy / cnt
            dn = math.hypot(cx - root[0], cy - root[1]) / max_d  # outwardness
            if rng.random() >= frond_density * (0.3 + 0.7 * dn):
                continue
            ul = math.hypot(sdx, sdy) or 1.0
            base = frond_size * (0.7 + 0.5 * min(cnt, 6) / 6.0)
            paths.extend(_frond_strokes(
                cx, cy, base, sdx / ul, sdy / ul,
                frond_lobes, frond_fill, frond_stroke, min_w, rng, W, H))
            if len(paths) >= FROND_CAP + n:
                break

    return paths
