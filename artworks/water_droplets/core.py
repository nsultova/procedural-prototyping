"""Water Droplets — concentric distorted ripple rings with cross-drop interference.

Pure port of water_droplets.py. Circles become point-sampled closed polylines
so the renderer only needs polylines. Random draws use the passed-in rng.
"""

import math

from engine.types import Path, Canvas

# Rarely-touched secondary knobs kept as constants (defaults from the original).
SECONDARY_DIST_MIN = 0.7
SECONDARY_DIST_MAX = 1.4
SECONDARY_DISTORTION = 0.0
SECONDARY_DIST_FREQ = 5
SECONDARY_DIST_GROWTH = 0.1


def _circle(cx, cy, r, n, width):
    pts = []
    for k in range(n):
        theta = 2 * math.pi * k / n
        pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return Path(points=pts, closed=True, width=width)


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    num_drops = int(p["num_drops"])
    max_rings = int(p["max_rings"])
    ring_spacing = p["ring_spacing"]
    ring_spacing_growth = p["ring_spacing_growth"]
    distortion = p["distortion"]
    freqs = [int(p["freq1"]), int(p["freq2"]), int(p["freq3"])]
    distortion_growth = p["distortion_growth"]
    interference_strength = p["interference_strength"]
    interference_wavelength_factor = p["interference_wavelength_factor"]
    secondary_drops = int(p["secondary_drops"])
    secondary_rings = int(p["secondary_rings"])
    secondary_ring_spacing = p["secondary_ring_spacing"]
    impact_rings = int(p["impact_rings"])
    impact_ring_spacing = p["impact_ring_spacing"]
    ring_points = int(p["ring_points"])
    stroke_width = p["stroke_width"]
    n_freqs = len(freqs)

    paths: list[Path] = []

    # Build drops (order of rng draws preserved from the original)
    drops = []
    for _ in range(num_drops):
        x = rng.uniform(W * 0.15, W * 0.85)
        y = rng.uniform(H * 0.15, H * 0.85)
        age = rng.uniform(0.4, 1.0)
        phases = [rng.uniform(0, 2 * math.pi) for _ in freqs]
        drops.append({"x": x, "y": y, "age": age, "phases": phases})

    # Guard div-by-zero for raw callers (UI mins keep the product >= 0.5).
    wavelength = max(ring_spacing * interference_wavelength_factor, 1e-9)

    for drop in drops:
        cx, cy = drop["x"], drop["y"]
        n_rings = max(2, int(max_rings * drop["age"]))

        # Ripple rings
        for ring_idx in range(n_rings):
            base_r = ring_spacing * (ring_spacing_growth ** ring_idx)
            dist_amp = distortion * (1.0 + distortion_growth * ring_idx)
            pts = []
            for i in range(ring_points):
                theta = 2 * math.pi * i / ring_points
                r = base_r
                for freq, phase in zip(freqs, drop["phases"]):
                    r += (dist_amp / n_freqs) * math.sin(freq * theta + phase)
                px = cx + base_r * math.cos(theta)
                py = cy + base_r * math.sin(theta)
                for other in drops:
                    if other is drop:
                        continue
                    dx = px - other["x"]
                    dy = py - other["y"]
                    dist = math.sqrt(dx * dx + dy * dy)
                    r += interference_strength * math.cos(2 * math.pi * dist / wavelength)
                pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
            paths.append(Path(points=pts, closed=True, width=stroke_width))

        # Impact center
        gap = ring_spacing * impact_ring_spacing
        for i in range(1, impact_rings + 1):
            paths.append(_circle(cx, cy, i * gap, max(24, ring_points // 4), stroke_width))

        # Secondary micro-splashes
        for _ in range(secondary_drops):
            angle = rng.uniform(0, 2 * math.pi)
            splash_dist = rng.uniform(
                ring_spacing * SECONDARY_DIST_MIN,
                ring_spacing * 2 + SECONDARY_DIST_MAX * 8,
            )
            sx = cx + splash_dist * math.cos(angle)
            sy = cy + splash_dist * math.sin(angle)
            if not (0 <= sx <= W and 0 <= sy <= H):
                # Skip before the ph0/ph1 draws (faithful to the original); note
                # this makes the rng draw count canvas-size-dependent by design.
                continue
            ph0 = rng.uniform(0, 2 * math.pi)
            ph1 = rng.uniform(0, 2 * math.pi)
            for j in range(1, secondary_rings + 1):
                base_r = j * secondary_ring_spacing
                dist_amp = SECONDARY_DISTORTION * (1 + SECONDARY_DIST_GROWTH * (j - 1))
                if dist_amp <= 0:
                    paths.append(_circle(sx, sy, base_r, max(24, ring_points // 4), stroke_width))
                else:
                    n_pts = max(32, int(ring_points * 0.35))
                    pts = []
                    for k in range(n_pts):
                        theta = 2 * math.pi * k / n_pts
                        r = base_r
                        r += dist_amp * math.sin(SECONDARY_DIST_FREQ * theta + ph0)
                        r += dist_amp * 0.4 * math.sin(SECONDARY_DIST_FREQ * 2.1 * theta + ph1)
                        pts.append((sx + r * math.cos(theta), sy + r * math.sin(theta)))
                    paths.append(Path(points=pts, closed=True, width=stroke_width))

    return paths
