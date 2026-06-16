"""Lichen Cells — branching skeleton with zone-differentiated Voronoi cells.

A Bézier branching skeleton defines territory zones; seed density and character
vary by distance to the nearest branch axis (needle cells → normal → large/void).
The perimeter of the branch union erupts into fine outward-radiating spine fringe.
"""

import math
import random
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Voronoi

from engine.types import Canvas, Path


@dataclass
class _Branch:
    pts: list      # list[tuple[float, float]] sampled along Bézier
    tangents: list # list[tuple[float, float]] unit tangent at each sample
    radius: float  # territory radius in mm
    depth: int     # 0 = primary arm, 1 = secondary tip


def _bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0],
        u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1],
    )


def _bezier_tangent(p0, p1, p2, p3, t):
    u = 1 - t
    dx = 3*(u**2*(p1[0]-p0[0]) + 2*u*t*(p2[0]-p1[0]) + t**2*(p3[0]-p2[0]))
    dy = 3*(u**2*(p1[1]-p0[1]) + 2*u*t*(p2[1]-p1[1]) + t**2*(p3[1]-p2[1]))
    mag = math.sqrt(dx*dx + dy*dy) + 1e-9
    return dx/mag, dy/mag


def _sample_branch(p0, p1, p2, p3, n=24):
    assert n >= 2
    pts, tans = [], []
    for i in range(n):
        t = i / (n - 1)
        pts.append(_bezier(p0, p1, p2, p3, t))
        tans.append(_bezier_tangent(p0, p1, p2, p3, t))
    return pts, tans


def _gen_skeleton(cx: float, cy: float, radius: float, n_primary: int,
                  angle_spread: float, irregularity: float, rng) -> list:
    """Branching Bézier skeleton: N primary arms + 1-3 secondary tips each."""
    branches = []

    for i in range(n_primary):
        base_angle = 2 * math.pi * i / n_primary + rng.uniform(-0.25, 0.25)
        prim_len = radius * rng.uniform(0.50, 0.72)
        prim_r = radius * rng.uniform(0.18, 0.30)

        p0 = (cx, cy)
        p3 = (cx + prim_len * math.cos(base_angle),
              cy + prim_len * math.sin(base_angle))
        ca = base_angle + rng.gauss(0, irregularity * 0.35)
        p1 = (cx + prim_len * 0.35 * math.cos(ca),
              cy + prim_len * 0.35 * math.sin(ca))
        cb = base_angle + rng.gauss(0, irregularity * 0.25)
        p2 = (p3[0] - prim_len * 0.20 * math.cos(cb),
              p3[1] - prim_len * 0.20 * math.sin(cb))

        pts, tans = _sample_branch(p0, p1, p2, p3)
        branches.append(_Branch(pts=pts, tangents=tans, radius=prim_r, depth=0))

        n_sec = rng.randint(1, 3)
        for _ in range(n_sec):
            sec_angle = base_angle + rng.uniform(-angle_spread, angle_spread)
            sec_len = radius * rng.uniform(0.18, 0.38)
            sec_r = prim_r * rng.uniform(0.45, 0.70)

            s0 = p3
            s3 = (p3[0] + sec_len * math.cos(sec_angle),
                  p3[1] + sec_len * math.sin(sec_angle))
            sc = sec_angle + rng.gauss(0, irregularity * 0.3)
            s1 = (s0[0] + sec_len * 0.4 * math.cos(sc),
                  s0[1] + sec_len * 0.4 * math.sin(sc))
            s2 = (s3[0] - sec_len * 0.2 * math.cos(sc),
                  s3[1] - sec_len * 0.2 * math.sin(sc))

            pts2, tans2 = _sample_branch(s0, s1, s2, s3)
            branches.append(_Branch(pts=pts2, tangents=tans2, radius=sec_r, depth=1))

    return branches


_BLOB_N = 300   # polygon vertex count for the organic blob outline


def _gen_blob(cx: float, cy: float, radius: float, n_lobes: int,
              roughness: float, rng) -> list:
    """Organic blob polygon via summed Fourier harmonics on a circle."""
    coeffs = []
    for k in range(2, n_lobes + 2):
        amp = roughness * abs(rng.gauss(0, 1)) / k
        phase = rng.uniform(0, 2 * math.pi)
        coeffs.append((k, amp, phase))
    pts = []
    for i in range(_BLOB_N):
        theta = 2 * math.pi * i / _BLOB_N
        r = radius + sum(radius * a * math.cos(k * theta + ph) for k, a, ph in coeffs)
        r = max(min(r, radius * 1.15), radius * 0.2)
        pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return pts


def _pip_batch(x: np.ndarray, y: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Vectorised ray-casting point-in-polygon for numpy arrays."""
    inside = np.zeros(len(x), dtype=bool)
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i, 0], poly[i, 1]
        xj, yj = poly[j, 0], poly[j, 1]
        cross = (yi > y) != (yj > y)
        denom = np.where(cross, yj - yi, 1.0)
        x_cross = (xj - xi) * (y - yi) / denom + xi
        inside ^= cross & (x < x_cross)
        j = i
    return inside


def _pip(x: float, y: float, poly: list) -> bool:
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _seg_t(x1, y1, x2, y2, x3, y3, x4, y4):
    """Parameter t along segment p1→p2 at its crossing with p3→p4, or None."""
    dx12, dy12 = x2 - x1, y2 - y1
    dx34, dy34 = x4 - x3, y4 - y3
    denom = dx12 * dy34 - dy12 * dx34
    if abs(denom) < 1e-10:
        return None
    t = ((x3 - x1) * dy34 - (y3 - y1) * dx34) / denom
    u = ((x3 - x1) * dy12 - (y3 - y1) * dx12) / denom
    return t if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None


def _clip_segment(p1, p2, polygon):
    """Clip segment to blob interior. Returns (a, b) or None."""
    x1, y1 = p1
    x2, y2 = p2
    in1 = _pip(x1, y1, polygon)
    in2 = _pip(x2, y2, polygon)
    if in1 and in2:
        return p1, p2
    hits = []
    n = len(polygon)
    for i in range(n):
        x3, y3 = polygon[i]
        x4, y4 = polygon[(i + 1) % n]
        t = _seg_t(x1, y1, x2, y2, x3, y3, x4, y4)
        if t is not None:
            hits.append((t, x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
    if not hits:
        return None
    hits.sort()
    if in1:
        return p1, (hits[0][1], hits[0][2])
    if in2:
        return (hits[-1][1], hits[-1][2]), p2
    if len(hits) >= 2:
        return (hits[0][1], hits[0][2]), (hits[-1][1], hits[-1][2])
    return None


def _gen_seeds(blob: list, cx: float, cy: float,
               n_seeds: int, edge_bias: float, rng) -> list:
    """Scatter Voronoi seeds biased toward blob boundary (more seeds → smaller cells at edge)."""
    poly_np = np.array(blob)
    min_x, max_x = float(poly_np[:, 0].min()), float(poly_np[:, 0].max())
    min_y, max_y = float(poly_np[:, 1].min()), float(poly_np[:, 1].max())
    rx = (max_x - min_x) * 0.5 + 1e-6
    ry = (max_y - min_y) * 0.5 + 1e-6

    seeds = []
    batch = max(n_seeds * 6, 200)
    while len(seeds) < n_seeds:
        cxs = np.array([rng.uniform(min_x, max_x) for _ in range(batch)])
        cys = np.array([rng.uniform(min_y, max_y) for _ in range(batch)])
        inside = _pip_batch(cxs, cys, poly_np)
        for x, y in zip(cxs[inside], cys[inside]):
            if len(seeds) >= n_seeds:
                break
            d = min(1.0, math.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
            # acceptance probability increases with distance from centre
            if rng.random() < 0.15 + 0.85 * d ** edge_bias:
                seeds.append([x, y])
    return seeds[:n_seeds]


def _voronoi_paths(seeds: list, blob: list, stroke_w: float) -> list:
    """Compute Voronoi, clip every ridge to the blob, return Paths."""
    arr = np.array(seeds, dtype=float)
    c = arr.mean(axis=0)
    pad = max(arr[:, 0].max() - arr[:, 0].min(),
              arr[:, 1].max() - arr[:, 1].min()) * 5.0 + 50.0
    corners = np.array([
        [c[0] - pad, c[1] - pad], [c[0] + pad, c[1] - pad],
        [c[0] - pad, c[1] + pad], [c[0] + pad, c[1] + pad],
    ])
    try:
        vor = Voronoi(np.vstack([arr, corners]))
    except Exception:
        return []
    paths = []
    for i, j in vor.ridge_vertices:
        if i < 0 or j < 0:
            continue
        v1 = tuple(vor.vertices[i])
        v2 = tuple(vor.vertices[j])
        seg = _clip_segment(v1, v2, blob)
        if seg:
            paths.append(Path(points=list(seg), closed=False, width=stroke_w))
    return paths


def _gen_fringe(blob: list, n_spines: int, spine_len: float,
                spine_width: float, stroke_w: float, rng) -> list:
    """Outward-radiating needle spines from blob boundary."""
    n = len(blob)
    cx = sum(p[0] for p in blob) / n
    cy = sum(p[1] for p in blob) / n
    paths = []
    for i in range(n_spines):
        idx = int(i * n / n_spines)
        bx, by = blob[idx]
        dx, dy = bx - cx, by - cy
        mag = math.sqrt(dx * dx + dy * dy) + 1e-9
        nx, ny = dx / mag, dy / mag   # outward normal
        tx, ty = -ny, nx              # tangent
        L = spine_len * rng.uniform(0.25, 1.0)
        W = spine_width * rng.uniform(0.4, 1.0)
        curve = rng.gauss(0, 0.12)
        tip = (bx + nx * L + tx * curve * L, by + ny * L + ty * curve * L)
        bl = (bx + tx * W / 2, by + ty * W / 2)
        br = (bx - tx * W / 2, by - ty * W / 2)
        paths.append(Path(points=[bl, tip, br], closed=False, width=stroke_w * 0.55))
    return paths


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    cell_count   = int(p["cell_count"])
    blob_rough   = p["blob_roughness"]
    blob_lobes   = int(p["blob_lobes"])
    edge_bias    = p["edge_bias"]
    spine_count  = int(p["spine_count"])
    spine_length = p["spine_length"]
    spine_width  = p["spine_width"]
    stroke_width = p["stroke_width"]

    cx, cy = W / 2, H / 2
    radius = min(W, H) * 0.38

    blob = _gen_blob(cx, cy, radius, blob_lobes, blob_rough,
                     random.Random(rng.randint(0, 2**31 - 1)))
    seeds = _gen_seeds(blob, cx, cy, cell_count, edge_bias,
                       random.Random(rng.randint(0, 2**31 - 1)))

    paths: list[Path] = []
    paths.append(Path(points=list(blob), closed=True, width=stroke_width))
    if len(seeds) >= 4:
        paths.extend(_voronoi_paths(seeds, blob, stroke_width))
    paths.extend(_gen_fringe(blob, spine_count, spine_length, spine_width, stroke_width,
                             random.Random(rng.randint(0, 2**31 - 1))))
    return paths
