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
    return paths
