"""Geological Strata — densely packed scanlines displaced by domain-warped fBm.

Pure port of the original geological_strata.py. Fix vs. original Python:
lacunarity & gain are now threaded into fbm so those knobs take effect
(the original stored them but never passed them through).
"""

import math
import random

from engine.types import Path, Canvas


_GRADS = tuple((math.cos(a), math.sin(a)) for a in
               (math.pi * 2 * i / 12 for i in range(12)))


def _build_perm(seed: int) -> list:
    rng = random.Random(seed)
    p = list(range(256))
    rng.shuffle(p)
    return p + p


def _dot(gi, fx, fy):
    g = _GRADS[gi]
    return g[0] * fx + g[1] * fy


def _noise2(x: float, y: float, perm: list) -> float:
    fx = math.floor(x)
    fy = math.floor(y)
    xi = int(fx) & 255
    yi = int(fy) & 255
    xf = x - fx
    yf = y - fy
    u = xf * xf * xf * (xf * (xf * 6.0 - 15.0) + 10.0)
    v = yf * yf * yf * (yf * (yf * 6.0 - 15.0) + 10.0)
    aa = perm[perm[xi] + yi] % 12
    ab = perm[perm[xi] + yi + 1] % 12
    ba = perm[perm[xi + 1] + yi] % 12
    bb = perm[perm[xi + 1] + yi + 1] % 12
    x1 = _dot(aa, xf, yf) + u * (_dot(ba, xf - 1, yf) - _dot(aa, xf, yf))
    x2 = _dot(ab, xf, yf - 1) + u * (_dot(bb, xf - 1, yf - 1) - _dot(ab, xf, yf - 1))
    return x1 + v * (x2 - x1)


def _fbm(x, y, perm, octaves, lacunarity, gain):
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0
    for _ in range(int(octaves)):
        total += _noise2(x * frequency, y * frequency, perm) * amplitude
        max_amp += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / max_amp if max_amp else 0.0


def _warped_fbm(x, y, perm, perm2, octaves, warp_strength, warp_scale,
                warp_octaves, lacunarity, gain):
    wx = _fbm(x * warp_scale, y * warp_scale, perm2, warp_octaves, lacunarity, gain) * warp_strength
    wy = _fbm(x * warp_scale + 5.2, y * warp_scale + 1.3, perm2, warp_octaves, lacunarity, gain) * warp_strength
    return _fbm(x + wx, y + wy, perm, octaves, lacunarity, gain)


def _edge_mask(x, y, perm, W, H, edge_inset, edge_roughness, edge_scale):
    w_denom = W * edge_inset + 1e-6
    h_denom = H * edge_inset + 1e-6
    dl = x / w_denom
    dr = (W - x) / w_denom
    dt = y / h_denom
    db = (H - y) / h_denom
    d = min(dl, dr, dt, db)
    if edge_roughness > 0:
        nv = _fbm(x * edge_scale, y * edge_scale, perm, 3, 2.0, 0.5)
        d += nv * edge_roughness * 0.8
    return max(0.0, min(1.0, d))


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    num_lines = int(p["num_lines"])
    x_res = max(int(p["x_resolution"]), 1)  # guard div-by-zero for raw callers
    noise_scale = p["noise_scale"]
    octaves = int(p["octaves"])
    lacunarity = p["lacunarity"]
    gain = p["gain"]
    warp_strength = p["warp_strength"]
    rel_warp_scale = p["warp_scale"] / max(noise_scale, 1e-6)
    warp_octaves = int(p["warp_octaves"])
    displacement = p["displacement"]
    edge_inset = p["edge_inset"]
    edge_roughness = p["edge_roughness"]
    edge_scale = p["edge_scale"]
    stroke_width = p["stroke_width"]

    # Permutation tables derived from the global seed via rng
    base_seed = rng.randint(0, 2**31 - 1)
    perm = _build_perm(base_seed)
    perm2 = _build_perm(base_seed + 12345)
    perm_edge = _build_perm(base_seed + 67890)

    paths: list[Path] = []
    denom = max(num_lines - 1, 1)
    for li in range(num_lines):
        base_y = (li / denom) * H
        points = []
        for xi in range(x_res + 1):
            x = (xi / x_res) * W
            disp = _warped_fbm(
                x * noise_scale, base_y * noise_scale,
                perm, perm2, octaves, warp_strength, rel_warp_scale,
                warp_octaves, lacunarity, gain,
            )
            y_disp = base_y + disp * displacement
            mask = _edge_mask(x, base_y, perm_edge, W, H,
                              edge_inset, edge_roughness, edge_scale)
            if mask < 0.01:
                if len(points) >= 2:
                    paths.append(Path(points=points, width=stroke_width))
                points = []
                continue
            points.append((x, y_disp))
        if len(points) >= 2:
            paths.append(Path(points=points, width=stroke_width))
    return paths
