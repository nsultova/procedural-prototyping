"""Slime Mould — branching vein network grown by space colonization, with a
thin reconnecting mesh layer and burst marks at junction nodes.

Two layers, pure (params + rng -> list[Path], deterministic):
  1. Veins   — space-colonization tree from a corner root; thickness from
               subtree size (Da Vinci), thick trunk tapering to fine tips.
  2. Mesh    — thin links between nearby, non-adjacent nodes -> loops ->
               enclosed cells/holes -> the reticulated organism interior.
  3. Bursts  — short radial marks at branch-junction nodes; concentrated
               tangles that add organic density at the nerve intersections.

All output is open polylines; tone comes from stroke density.
"""

import math
from collections import defaultdict

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
                    px, py = -(ny - y) / dist, (nx - x) / dist
                    links.append(Path(points=[(x, y),
                                              (mx + px * sag, my + py * sag),
                                              (nx, ny)], width=width))
                    if len(links) >= cap:
                        return links
    return links


def _junction_bursts(nodes, children, burst_density, burst_strokes, burst_reach,
                     burst_length, min_w, rng, W, H):
    """Short radial marks at branch-junction nodes — dense organic tangle at nerve crossings."""
    paths = []
    for i, node_children in enumerate(children):
        degree = len(node_children)
        if degree < 2:
            continue
        if rng.random() >= burst_density:
            continue
        x, y = nodes[i]
        deg_frac = min(degree, 5) / 5.0
        n = max(2, int(burst_strokes * (0.5 + 0.7 * rng.random()) * (0.7 + 0.3 * deg_frac)))
        reach = burst_reach * (0.8 + 0.4 * deg_frac)
        for _ in range(n):
            ang = rng.random() * 2 * math.pi
            r_start = reach * rng.random() ** 0.5 * 0.4
            sx = x + math.cos(ang) * r_start
            sy = y + math.sin(ang) * r_start
            L = burst_length * (0.4 + 0.8 * rng.random())
            ex = sx + math.cos(ang) * L
            ey = sy + math.sin(ang) * L
            # slight organic curve
            perp = ang + math.pi / 2
            curl = (rng.random() - 0.5) * L * 0.45
            mx = (sx + ex) * 0.5 + math.cos(perp) * curl
            my = (sy + ey) * 0.5 + math.sin(perp) * curl
            paths.append(Path(points=[
                (min(max(sx, 0.0), W), min(max(sy, 0.0), H)),
                (min(max(mx, 0.0), W), min(max(my, 0.0), H)),
                (min(max(ex, 0.0), W), min(max(ey, 0.0), H)),
            ], width=min_w))
    return paths


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
    mesh_density = p["mesh_density"]
    mesh_dist = p["mesh_dist"]
    burst_density = p["burst_density"]
    burst_strokes = p["burst_strokes"]
    burst_reach = p["burst_reach"]
    burst_length = p["burst_length"]

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
        pulls = defaultdict(lambda: [0.0, 0.0])
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
            pulls[ni][0] += (ax - nx) * inv
            pulls[ni][1] += (ay - ny) * inv
        active = survivors

        if pulls:
            for ni, (dx, dy) in pulls.items():
                mag = math.hypot(dx, dy)
                if mag < 1e-9:
                    continue
                grow(ni, dx / mag, dy / mag)
        elif active:
            best_d, best_ni, best_ax, best_ay = float("inf"), -1, 0.0, 0.0
            for (ax, ay) in active[:200]:
                for i in range(len(nodes)):
                    nx, ny = nodes[i]
                    d = math.hypot(ax - nx, ay - ny)
                    if d < best_d:
                        best_d, best_ni, best_ax, best_ay = d, i, ax, ay
            if best_ni < 0:
                break
            nx, ny = nodes[best_ni]
            dd = best_d or 1.0
            grow(best_ni, (best_ax - nx) / dd, (best_ay - ny) / dd)
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
        return min_w + (max_w - min_w) * norm ** w_exp

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

    # --- junction bursts: radial marks at branch nodes ---
    if burst_density > 0 and burst_strokes > 0:
        paths.extend(_junction_bursts(
            nodes, children, burst_density, burst_strokes,
            burst_reach, burst_length, min_w, rng, W, H))

    return paths
