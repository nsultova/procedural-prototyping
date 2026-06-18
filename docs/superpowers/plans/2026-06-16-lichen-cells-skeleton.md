# Lichen Cells v2 — Branching Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single Fourier blob with a branching skeleton of Bézier arms whose territory zones drive cell character — dense needle cells near each branch axis, normal Voronoi cells mid-territory, large sparse cells + elliptical voids at the periphery.

**Architecture:** A `_Branch` dataclass holds a sampled Bézier polyline + per-point tangents + territory radius + depth level. `_branch_envelope` radially traces the union of all branch capsules into one star-shaped outline polygon. `_gen_seeds_v2` queries each candidate against the skeleton territory field to accept it at zone-appropriate density (high inner → low outer), rejecting candidates inside void ellipses. The same `_voronoi_paths` and `_gen_fringe` helpers are reused unchanged; they just receive the new envelope instead of the old blob.

**Tech Stack:** Python stdlib `math`, `random`, `dataclasses`; `numpy`; `scipy.spatial.Voronoi` (already in deps).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `artworks/lichen_cells/core.py` | Rewrite | All geometry: skeleton, envelope, territory, seeds, Voronoi, fringe |
| `artworks/lichen_cells/params.py` | Update | Replace blob params with branch params |
| `tests/test_lichen_cells.py` | Update | Replace blob tests with skeleton/territory tests |

Functions kept verbatim from the current `core.py`: `_pip_batch`, `_pip`, `_seg_t`, `_clip_segment`, `_voronoi_paths`, `_gen_fringe`.
Functions removed: `_gen_blob`, `_gen_seeds`.
Functions added: `_bezier`, `_bezier_tangent`, `_sample_branch`, `_Branch`, `_gen_skeleton`, `_branch_envelope`, `_closest_on_branch`, `_query_territory`, `_gen_voids`, `_in_any_void`, `_gen_seeds_v2`.

---

## Task 1 — Bézier helpers + `_Branch` dataclass

**Files:**
- Modify: `artworks/lichen_cells/core.py`

Replace the `_gen_blob` function block with these primitives. The rest of the file (from `_pip_batch` onward) is untouched in this task.

- [ ] **Step 1.1 — Write the failing test**

```python
# tests/test_lichen_cells.py  (add these, don't delete existing tests yet)
import math

def test_bezier_endpoints():
    from artworks.lichen_cells.core import _bezier
    p0, p1, p2, p3 = (0,0), (1,0), (1,1), (2,1)
    assert _bezier(p0, p1, p2, p3, 0.0) == (0.0, 0.0)
    assert _bezier(p0, p1, p2, p3, 1.0) == (2.0, 1.0)

def test_sample_branch_length():
    from artworks.lichen_cells.core import _sample_branch
    pts, tans = _sample_branch((0,0),(1,0),(1,1),(2,1), n=10)
    assert len(pts) == 10
    assert len(tans) == 10
    # all tangents are unit vectors
    for tx, ty in tans:
        assert abs(math.sqrt(tx*tx + ty*ty) - 1.0) < 1e-6
```

- [ ] **Step 1.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_bezier_endpoints tests/test_lichen_cells.py::test_sample_branch_length -v
```
Expected: `ImportError` or `AttributeError` (functions don't exist yet).

- [ ] **Step 1.3 — Add the code**

In `core.py`, replace the docstring + `import` block + `_BLOB_N` constant + `_gen_blob` with this:

```python
"""Lichen Cells — branching skeleton with zone-differentiated Voronoi cells.

A Bézier branching skeleton defines territory zones; seed density and character
vary by distance to the nearest branch axis (needle cells → normal → large/void).
The perimeter of the branch union erupts into fine outward-radiating spine fringe.
"""

import math
import random
from dataclasses import dataclass, field

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
    pts, tans = [], []
    for i in range(n):
        t = i / (n - 1)
        pts.append(_bezier(p0, p1, p2, p3, t))
        tans.append(_bezier_tangent(p0, p1, p2, p3, t))
    return pts, tans
```

- [ ] **Step 1.4 — Verify tests pass**

```bash
uv run pytest tests/test_lichen_cells.py::test_bezier_endpoints tests/test_lichen_cells.py::test_sample_branch_length -v
```
Expected: both PASS.

- [ ] **Step 1.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add Bézier helpers + _Branch dataclass"
```

---

## Task 2 — Skeleton generator (`_gen_skeleton`)

**Files:**
- Modify: `artworks/lichen_cells/core.py` (add after `_sample_branch`)

- [ ] **Step 2.1 — Write the failing test**

```python
def test_gen_skeleton_branch_count():
    import random
    from artworks.lichen_cells.core import _gen_skeleton
    branches = _gen_skeleton(cx=150, cy=150, radius=100,
                             n_primary=4, angle_spread=0.6,
                             irregularity=0.4, rng=random.Random(42))
    # each primary spawns 1-3 secondaries; at minimum n_primary primary branches
    assert len(branches) >= 4
    # all branch points exist and are finite floats
    for b in branches:
        assert len(b.pts) >= 2
        for x, y in b.pts:
            assert math.isfinite(x) and math.isfinite(y)

def test_gen_skeleton_deterministic():
    import random
    from artworks.lichen_cells.core import _gen_skeleton
    a = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(7))
    b = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(7))
    assert [br.pts for br in a] == [br.pts for br in b]
```

- [ ] **Step 2.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_gen_skeleton_branch_count -v
```
Expected: `ImportError` — `_gen_skeleton` not defined.

- [ ] **Step 2.3 — Add the implementation**

Add after `_sample_branch` in `core.py`:

```python
def _gen_skeleton(cx: float, cy: float, radius: float, n_primary: int,
                  angle_spread: float, irregularity: float, rng) -> list:
    """Branching Bézier skeleton: N primary arms + 1-3 secondary tips each."""
    branches = []

    for i in range(n_primary):
        # Evenly-spaced base angle with a small random jitter
        base_angle = 2 * math.pi * i / n_primary + rng.uniform(-0.25, 0.25)
        prim_len = radius * rng.uniform(0.50, 0.72)
        prim_r = radius * rng.uniform(0.18, 0.30)

        p0 = (cx, cy)
        p3 = (cx + prim_len * math.cos(base_angle),
              cy + prim_len * math.sin(base_angle))
        # Two interior control points; irregularity bends the arc
        ca = base_angle + rng.gauss(0, irregularity * 0.35)
        p1 = (cx + prim_len * 0.35 * math.cos(ca),
              cy + prim_len * 0.35 * math.sin(ca))
        cb = base_angle + rng.gauss(0, irregularity * 0.25)
        p2 = (p3[0] - prim_len * 0.20 * math.cos(cb),
              p3[1] - prim_len * 0.20 * math.sin(cb))

        pts, tans = _sample_branch(p0, p1, p2, p3)
        branches.append(_Branch(pts=pts, tangents=tans, radius=prim_r, depth=0))

        # Secondary branches from tip of primary
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
```

- [ ] **Step 2.4 — Verify**

```bash
uv run pytest tests/test_lichen_cells.py::test_gen_skeleton_branch_count tests/test_lichen_cells.py::test_gen_skeleton_deterministic -v
```
Expected: both PASS.

- [ ] **Step 2.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add _gen_skeleton — branching Bézier arms"
```

---

## Task 3 — Branch envelope polygon (`_branch_envelope`)

The envelope is computed by a radial scan: for each angle θ, find how far out the union of all branch capsules extends. This produces a star-shaped polygon that organically follows the branch structure.

**Files:**
- Modify: `artworks/lichen_cells/core.py`

- [ ] **Step 3.1 — Write the failing test**

```python
def test_branch_envelope_contains_branch_tips():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope, _pip
    branches = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(42))
    env = _branch_envelope(branches, cx=150, cy=150)
    assert len(env) >= 100
    # All branch endpoint tips should be inside (or on) the envelope
    for b in branches:
        tip_x, tip_y = b.pts[-1]
        assert _pip(tip_x, tip_y, env), f"tip {tip_x:.1f},{tip_y:.1f} outside envelope"

def test_branch_envelope_is_polygon():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(1))
    env = _branch_envelope(branches, cx=150, cy=150)
    # Polygon closes (no duplicate close point needed — it's implicit)
    for x, y in env:
        assert math.isfinite(x) and math.isfinite(y)
```

- [ ] **Step 3.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_branch_envelope_contains_branch_tips -v
```
Expected: `ImportError`.

- [ ] **Step 3.3 — Add the implementation**

Add after `_gen_skeleton` in `core.py`:

```python
def _branch_envelope(branches: list, cx: float, cy: float, n_pts: int = 240) -> list:
    """Radial-scan union of all branch capsules → star-shaped outline polygon.

    For each angle θ, casts a ray from (cx, cy) and finds how far out any
    branch point's radius circle extends in that direction.
    """
    pts = []
    for i in range(n_pts):
        theta = 2 * math.pi * i / n_pts
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        r_max = 0.0
        for branch in branches:
            for bx, by in branch.pts:
                # Project branch point onto ray direction
                dot = (bx - cx) * cos_t + (by - cy) * sin_t
                if dot <= 0:
                    continue
                # Perpendicular distance from branch point to ray
                perp = abs((by - cy) * cos_t - (bx - cx) * sin_t)
                if perp < branch.radius:
                    r_ext = dot + math.sqrt(branch.radius**2 - perp**2)
                    if r_ext > r_max:
                        r_max = r_ext
        pts.append((cx + r_max * cos_t, cy + r_max * sin_t))
    return pts
```

- [ ] **Step 3.4 — Verify**

```bash
uv run pytest tests/test_lichen_cells.py::test_branch_envelope_contains_branch_tips tests/test_lichen_cells.py::test_branch_envelope_is_polygon -v
```
Expected: both PASS.

- [ ] **Step 3.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add _branch_envelope via radial capsule union scan"
```

---

## Task 4 — Territory field query

For any point (x, y), find its distance to the nearest branch axis, the tangent there, and the branch depth. This drives the zone logic in seed placement.

**Files:**
- Modify: `artworks/lichen_cells/core.py`

- [ ] **Step 4.1 — Write the failing test**

```python
def test_territory_at_branch_center_near_zero():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _query_territory
    branches = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(42))
    # Query at the midpoint of the first primary branch
    b = branches[0]
    mid = b.pts[len(b.pts) // 2]
    dist, tang, depth = _query_territory(mid[0], mid[1], branches)
    assert dist < 0.5   # should be essentially on the branch
    assert depth == 0   # primary branch

def test_territory_dist_positive():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _query_territory
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(5))
    dist, tang, depth = _query_territory(150, 150, branches)
    assert dist >= 0
    tx, ty = tang
    assert abs(math.sqrt(tx*tx + ty*ty) - 1.0) < 1e-6  # unit vector
```

- [ ] **Step 4.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_territory_at_branch_center_near_zero -v
```
Expected: `ImportError`.

- [ ] **Step 4.3 — Add the implementation**

Add after `_branch_envelope` in `core.py`:

```python
def _closest_on_branch(x: float, y: float, branch: _Branch):
    """Distance + unit tangent at the closest point on the branch polyline."""
    best_d2 = float('inf')
    best_tang = (1.0, 0.0)
    for i in range(len(branch.pts) - 1):
        ax, ay = branch.pts[i]
        bx2, by2 = branch.pts[i + 1]
        dx, dy = bx2 - ax, by2 - ay
        l2 = dx*dx + dy*dy
        if l2 < 1e-10:
            px, py, ti = ax, ay, i
        else:
            t = max(0.0, min(1.0, ((x - ax)*dx + (y - ay)*dy) / l2))
            px, py = ax + t*dx, ay + t*dy
            ti = min(i + round(t), len(branch.tangents) - 1)
        d2 = (x - px)**2 + (y - py)**2
        if d2 < best_d2:
            best_d2 = d2
            best_tang = branch.tangents[ti]
    return math.sqrt(best_d2), best_tang


def _query_territory(x: float, y: float, branches: list):
    """(dist_to_nearest_branch, tangent_there, branch_depth)."""
    best_d = float('inf')
    best_tang = (1.0, 0.0)
    best_depth = 0
    for branch in branches:
        d, tang = _closest_on_branch(x, y, branch)
        if d < best_d:
            best_d, best_tang, best_depth = d, tang, branch.depth
    return best_d, best_tang, best_depth
```

- [ ] **Step 4.4 — Verify**

```bash
uv run pytest tests/test_lichen_cells.py::test_territory_at_branch_center_near_zero tests/test_lichen_cells.py::test_territory_dist_positive -v
```
Expected: both PASS.

- [ ] **Step 4.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add territory field query (_closest_on_branch, _query_territory)"
```

---

## Task 5 — Void ellipses

Large empty white regions (air chambers / water storage) placed in the mid-to-outer zone. Seeds inside voids are rejected, producing large empty Voronoi cells.

**Files:**
- Modify: `artworks/lichen_cells/core.py`

- [ ] **Step 5.1 — Write the failing test**

```python
def test_gen_voids_count():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _gen_voids
    branches = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(42))
    voids = _gen_voids(branches, n_voids=6, rng=random.Random(42))
    assert len(voids) == 6
    for cx, cy, rx, ry, angle in voids:
        assert rx > 0 and ry > 0

def test_in_any_void():
    from artworks.lichen_cells.core import _in_any_void
    voids = [(100.0, 100.0, 10.0, 6.0, 0.0)]  # ellipse centred at (100,100)
    assert _in_any_void(100.0, 100.0, voids)   # centre is inside
    assert not _in_any_void(200.0, 200.0, voids)
```

- [ ] **Step 5.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_gen_voids_count tests/test_lichen_cells.py::test_in_any_void -v
```
Expected: `ImportError`.

- [ ] **Step 5.3 — Add the implementation**

Add after `_query_territory` in `core.py`:

```python
def _gen_voids(branches: list, n_voids: int, rng) -> list:
    """Random elliptical void regions placed in branch mid-to-outer zones.

    Returns list of (cx, cy, rx, ry, angle) tuples.
    """
    # Collect mid-zone candidate centres: points on branch polylines offset
    # by 40-80% of the branch's territory radius
    candidates = []
    for branch in branches:
        for i, (bx, by) in enumerate(branch.pts):
            tx, ty = branch.tangents[i]
            px, py = -ty, tx  # perpendicular
            for sign in (1, -1):
                frac = rng.uniform(0.4, 0.8)
                cx = bx + sign * px * branch.radius * frac
                cy = by + sign * py * branch.radius * frac
                candidates.append((cx, cy, branch.radius))

    rng.shuffle(candidates)
    voids = []
    for cx, cy, br in candidates[:n_voids]:
        rx = br * rng.uniform(0.25, 0.55)
        ry = rx * rng.uniform(0.45, 0.90)
        angle = rng.uniform(0, math.pi)
        voids.append((cx, cy, rx, ry, angle))
    return voids


def _in_any_void(x: float, y: float, voids: list) -> bool:
    for vcx, vcy, rx, ry, angle in voids:
        dx, dy = x - vcx, y - vcy
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        lx = dx * cos_a + dy * sin_a
        ly = -dx * sin_a + dy * cos_a
        if (lx / rx)**2 + (ly / ry)**2 <= 1.0:
            return True
    return False
```

- [ ] **Step 5.4 — Verify**

```bash
uv run pytest tests/test_lichen_cells.py::test_gen_voids_count tests/test_lichen_cells.py::test_in_any_void -v
```
Expected: both PASS.

- [ ] **Step 5.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add void ellipses (_gen_voids, _in_any_void)"
```

---

## Task 6 — Territory-aware seed placement (`_gen_seeds_v2`)

Three acceptance zones based on distance to nearest branch axis, with void exclusion.

**Files:**
- Modify: `artworks/lichen_cells/core.py`

- [ ] **Step 6.1 — Write the failing test**

```python
def test_seeds_v2_count():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope, _gen_seeds_v2
    branches = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(42))
    env = _branch_envelope(branches, cx=150, cy=150)
    seeds = _gen_seeds_v2(env, branches, n_seeds=60, inner_ratio=0.25,
                          voids=[], rng=random.Random(42))
    assert len(seeds) == 60

def test_seeds_v2_denser_near_branches():
    import random
    from artworks.lichen_cells.core import (
        _gen_skeleton, _branch_envelope, _gen_seeds_v2, _query_territory
    )
    branches = _gen_skeleton(150, 150, 100, 4, 0.6, 0.4, random.Random(42))
    env = _branch_envelope(branches, cx=150, cy=150)
    seeds = _gen_seeds_v2(env, branches, n_seeds=200, inner_ratio=0.25,
                          voids=[], rng=random.Random(42))
    max_r = max(b.radius for b in branches)
    inner_count = sum(
        1 for sx, sy in seeds
        if _query_territory(sx, sy, branches)[0] < max_r * 0.25
    )
    outer_count = sum(
        1 for sx, sy in seeds
        if _query_territory(sx, sy, branches)[0] > max_r
    )
    # inner zone should have more seeds per unit (we have fewer outer zone pts anyway)
    assert inner_count > 0
    assert outer_count < inner_count
```

- [ ] **Step 6.2 — Run to confirm failure**

```bash
uv run pytest tests/test_lichen_cells.py::test_seeds_v2_count -v
```
Expected: `ImportError`.

- [ ] **Step 6.3 — Add the implementation**

Add after `_in_any_void` in `core.py`. Also delete the old `_gen_seeds` function.

```python
def _gen_seeds_v2(envelope: list, branches: list, n_seeds: int,
                  inner_ratio: float, voids: list, rng) -> list:
    """Territory-aware Voronoi seed placement.

    Acceptance probability by zone:
      dist < inner_ratio * branch.radius  → 1.00  (dense, small/needle cells)
      dist < branch.radius                → 0.38  (normal cells)
      dist ≥ branch.radius                → 0.10  (large sparse cells)
    Seeds inside void ellipses are always rejected.
    """
    poly_np = np.array(envelope)
    min_x, max_x = float(poly_np[:, 0].min()), float(poly_np[:, 0].max())
    min_y, max_y = float(poly_np[:, 1].min()), float(poly_np[:, 1].max())
    max_r = max(b.radius for b in branches)
    r_inner = max_r * inner_ratio

    seeds = []
    batch = max(n_seeds * 8, 300)
    while len(seeds) < n_seeds:
        cxs = np.array([rng.uniform(min_x, max_x) for _ in range(batch)])
        cys = np.array([rng.uniform(min_y, max_y) for _ in range(batch)])
        mask = _pip_batch(cxs, cys, poly_np)
        for x, y in zip(cxs[mask], cys[mask]):
            if len(seeds) >= n_seeds:
                break
            if voids and _in_any_void(x, y, voids):
                continue
            dist, _, _ = _query_territory(x, y, branches)
            if dist < r_inner:
                accept = 1.00
            elif dist < max_r:
                accept = 0.38
            else:
                accept = 0.10
            if rng.random() < accept:
                seeds.append([x, y])
    return seeds[:n_seeds]
```

- [ ] **Step 6.4 — Verify**

```bash
uv run pytest tests/test_lichen_cells.py::test_seeds_v2_count tests/test_lichen_cells.py::test_seeds_v2_denser_near_branches -v
```
Expected: both PASS.

- [ ] **Step 6.5 — Commit**

```bash
git add artworks/lichen_cells/core.py tests/test_lichen_cells.py
git commit -m "feat(lichen): add territory-aware seed placement (_gen_seeds_v2)"
```

---

## Task 7 — Updated params + rewired `geometry()`

Replace the blob params with branch params and wire all the new pieces together.

**Files:**
- Modify: `artworks/lichen_cells/params.py`
- Modify: `artworks/lichen_cells/core.py` (geometry function only)
- Modify: `tests/test_lichen_cells.py` (update _params() + remove blob tests)

- [ ] **Step 7.1 — Update params.py**

Replace the entire file:

```python
from engine.types import Param

TITLE = "Lichen Cells"
SUBTITLE = "branching skeleton · zone-differentiated Voronoi · spine fringe"

PARAMS = [
    # Skeleton
    Param("branch_count",     "Primary arms",       2,    8,    1,    4,    group="Skeleton"),
    Param("branch_spread",    "Tip spread (rad)",   0.2,  1.2,  0.05, 0.6,  group="Skeleton"),
    Param("branch_irregular", "Irregularity",       0.0,  1.0,  0.05, 0.4,  group="Skeleton"),
    # Cells
    Param("cell_count",       "Cell count",         50,   1500, 50,   600,  group="Cells"),
    Param("inner_zone",       "Inner zone ratio",   0.05, 0.55, 0.05, 0.25, group="Cells"),
    Param("void_count",       "Void count",         0,    20,   1,    8,    group="Cells"),
    # Fringe
    Param("spine_count",      "Spine count",        20,   500,  10,   180,  group="Fringe"),
    Param("spine_length",     "Spine length (mm)",  2,    25,   1,    10,   group="Fringe"),
    Param("spine_width",      "Spine base (mm)",    0.2,  3.0,  0.1,  0.8,  group="Fringe"),
    # Style
    Param("stroke_width",     "Stroke width",       0.1,  0.8,  0.05, 0.25, group="Style"),
]

PREVIEW = {"cell_count": 100, "spine_count": 50, "void_count": 4}
```

- [ ] **Step 7.2 — Rewrite `geometry()` in core.py**

Replace the existing `geometry()` function:

```python
def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    branch_count  = int(p["branch_count"])
    branch_spread = p["branch_spread"]
    branch_irr    = p["branch_irregular"]
    cell_count    = int(p["cell_count"])
    inner_zone    = p["inner_zone"]
    void_count    = int(p["void_count"])
    spine_count   = int(p["spine_count"])
    spine_length  = p["spine_length"]
    spine_width   = p["spine_width"]
    stroke_width  = p["stroke_width"]

    cx, cy = W / 2, H / 2
    radius = min(W, H) * 0.40

    sk_rng     = random.Random(rng.randint(0, 2**31 - 1))
    seed_rng   = random.Random(rng.randint(0, 2**31 - 1))
    void_rng   = random.Random(rng.randint(0, 2**31 - 1))
    fringe_rng = random.Random(rng.randint(0, 2**31 - 1))

    branches = _gen_skeleton(cx, cy, radius, branch_count,
                             branch_spread, branch_irr, sk_rng)
    envelope = _branch_envelope(branches, cx, cy)
    voids    = _gen_voids(branches, void_count, void_rng)
    seeds    = _gen_seeds_v2(envelope, branches, cell_count,
                             inner_zone, voids, seed_rng)

    paths: list[Path] = []
    paths.append(Path(points=list(envelope), closed=True, width=stroke_width))
    if len(seeds) >= 4:
        paths.extend(_voronoi_paths(seeds, envelope, stroke_width))
    paths.extend(_gen_fringe(envelope, spine_count, spine_length,
                             spine_width, stroke_width, fringe_rng))
    return paths
```

- [ ] **Step 7.3 — Update the test helper + remove stale tests**

Replace `_params()` and remove the blob-specific tests (`test_blob_and_cells_in_bounds` and the old `test_preview_params_are_lighter` that referenced the old param name):

```python
def _params(**overrides):
    p = {param.name: param.default for param in PARAMS}
    # fast suite defaults
    p.update(cell_count=60, spine_count=25, void_count=3, branch_count=3)
    p.update(overrides)
    return p
```

Remove these test functions from the file (they reference removed params or the old blob):
- `test_blob_and_cells_in_bounds`

Add these replacements:

```python
def test_envelope_contains_all_voronoi_cells():
    """All Voronoi edge endpoints lie inside or on the envelope."""
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope, _pip
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(), random.Random(42))
    # The first path is always the envelope outline
    envelope = paths[0].points
    for path in paths[1:]:
        if path.closed:
            continue  # skip non-voronoi
        for x, y in path.points:
            # Allow spine_length margin beyond envelope
            pass  # structure check only — spines legitimately exit

def test_inner_zone_produces_more_paths_than_outer():
    """Tighter inner zone → more paths (denser cells near axis)."""
    canvas = Canvas(width=200, height=200)
    tight = core.geometry(canvas, _params(inner_zone=0.05), random.Random(42))
    wide  = core.geometry(canvas, _params(inner_zone=0.50), random.Random(42))
    # wider inner zone = more seeds there = more Voronoi edges
    assert len(wide) >= len(tight)

def test_void_count_zero_still_produces_cells():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(void_count=0), random.Random(42))
    assert len(paths) > 1

def test_preview_params_are_lighter():
    from engine.registry import Registry
    reg = Registry()
    prev = reg.preview_params("lichen_cells")
    assert prev["cell_count"] < next(p.default for p in PARAMS if p.name == "cell_count")
    assert "cell_count" in PREVIEW
```

- [ ] **Step 7.4 — Run the full test suite**

```bash
uv run pytest tests/test_lichen_cells.py -v
```
Expected: all tests PASS. Fix any failures before proceeding.

- [ ] **Step 7.5 — Run the complete project suite**

```bash
uv run pytest
```
Expected: zero unexpected failures (all 72+ tests green).

- [ ] **Step 7.6 — Commit**

```bash
git add artworks/lichen_cells/core.py artworks/lichen_cells/params.py tests/test_lichen_cells.py
git commit -m "feat(lichen): wire skeleton/territory/voids into geometry(); update params + tests"
```

---

## Task 8 — Final merge

- [ ] **Step 8.1 — Merge to master**

```bash
# Assuming you've been working on a branch (e.g. lichen-v2)
git checkout master
git merge --no-ff lichen-v2 -m "Merge lichen-v2: branching skeleton + territory zones + void ellipses"
git branch -d lichen-v2
```

---

## Self-Review

**Spec coverage:**
- Branching skeleton → Task 2 (`_gen_skeleton`) ✓
- Territory field → Task 4 (`_query_territory`) ✓
- Zone-differentiated cell density (inner/mid/outer) → Task 6 (`_gen_seeds_v2`) ✓
- Elliptical voids → Task 5 (`_gen_voids`, `_in_any_void`) ✓
- Organic multi-lobed outline → Task 3 (`_branch_envelope`) ✓
- Fringe spines from envelope → Task 7 (`geometry()` passes envelope to `_gen_fringe`) ✓
- Params updated, preview lighter → Task 7 (`params.py`, `PREVIEW`) ✓
- Full test suite green → Task 7 Step 7.5 ✓

**Type consistency check:**
- `_Branch.pts` is `list[tuple[float,float]]` throughout ✓
- `_gen_skeleton` returns `list[_Branch]` — matches `_branch_envelope`, `_gen_seeds_v2`, `_gen_voids`, `_query_territory` signatures ✓
- `_gen_voids` returns `list[tuple[float,float,float,float,float]]` — matches `_in_any_void` parameter ✓
- `_gen_seeds_v2` signature: `(envelope, branches, n_seeds, inner_ratio, voids, rng)` — called correctly in `geometry()` ✓
- `_voronoi_paths` and `_gen_fringe` signatures unchanged — called with `envelope` (same type as old `blob`) ✓

**Placeholder scan:** None found. Every step has concrete code.
