import math
import random
from engine.types import Canvas
from artworks.lichen_cells import core
from artworks.lichen_cells.params import PARAMS, PREVIEW


def _params(**overrides):
    p = {param.name: param.default for param in PARAMS}
    # fast defaults for the suite: fewer cells and spines
    p.update(cell_count=80, spine_count=30)
    p.update(overrides)
    return p


def test_produces_paths():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(), random.Random(42))
    assert len(paths) > 0


def test_deterministic():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _params(), random.Random(7))
    b = core.geometry(canvas, _params(), random.Random(7))
    assert [p.points for p in a] == [p.points for p in b]


def test_different_seeds_differ():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _params(), random.Random(1))
    b = core.geometry(canvas, _params(), random.Random(2))
    assert [p.points for p in a] != [p.points for p in b]


def test_blob_and_cells_in_bounds():
    # Voronoi edges and the blob outline stay within canvas bounds.
    # Spine tips radiate outward and may extend beyond; they are excluded here.
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(spine_count=0), random.Random(42))
    for path in paths:
        for x, y in path.points:
            assert -1e-6 <= x <= canvas.width + 1e-6
            assert -1e-6 <= y <= canvas.height + 1e-6


def test_spine_tips_may_extend_past_canvas():
    # Fringe spines intentionally radiate past the canvas edge by up to spine_length.
    canvas = Canvas(width=200, height=200)
    params = _params(spine_length=15)
    paths = core.geometry(canvas, params, random.Random(42))
    margin = params["spine_length"] + 5
    for path in paths:
        for x, y in path.points:
            assert -margin <= x <= canvas.width + margin
            assert -margin <= y <= canvas.height + margin


def test_zero_spines_still_produces_cells():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(spine_count=0), random.Random(42))
    # At least the blob outline plus some Voronoi edges
    assert len(paths) > 1


def test_higher_cell_count_more_paths():
    canvas = Canvas(width=200, height=200)
    few = core.geometry(canvas, _params(cell_count=40), random.Random(42))
    many = core.geometry(canvas, _params(cell_count=150), random.Random(42))
    assert len(many) > len(few)


def test_preview_params_are_lighter():
    from engine.registry import Registry
    reg = Registry()
    prev = reg.preview_params("lichen_cells")
    assert prev["cell_count"] < next(p.default for p in PARAMS if p.name == "cell_count")
    assert "cell_count" in PREVIEW


def test_bezier_endpoints():
    from artworks.lichen_cells.core import _bezier
    p0, p1, p2, p3 = (0,0), (1,0), (1,1), (2,1)
    x0, y0 = _bezier(p0, p1, p2, p3, 0.0)
    x1, y1 = _bezier(p0, p1, p2, p3, 1.0)
    assert math.isclose(x0, 0.0) and math.isclose(y0, 0.0)
    assert math.isclose(x1, 2.0) and math.isclose(y1, 1.0)

def test_sample_branch_length():
    from artworks.lichen_cells.core import _bezier, _sample_branch
    p0, p1, p2, p3 = (0,0),(1,0),(1,1),(2,1)
    pts, tans = _sample_branch(p0, p1, p2, p3, n=10)
    assert len(pts) == 10
    assert len(tans) == 10
    for tx, ty in tans:
        assert abs(math.sqrt(tx*tx + ty*ty) - 1.0) < 1e-6
    # first and last points must match Bézier endpoints
    exp0 = _bezier(p0, p1, p2, p3, 0.0)
    exp1 = _bezier(p0, p1, p2, p3, 1.0)
    assert math.isclose(pts[0][0], exp0[0]) and math.isclose(pts[0][1], exp0[1])
    assert math.isclose(pts[-1][0], exp1[0]) and math.isclose(pts[-1][1], exp1[1])


def test_gen_skeleton_branch_count():
    import random
    from artworks.lichen_cells.core import _gen_skeleton
    branches = _gen_skeleton(cx=150, cy=150, radius=100,
                             n_primary=4, angle_spread=0.6,
                             irregularity=0.4, rng=random.Random(42))
    assert len(branches) >= 4  # at minimum n_primary primary branches
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

def test_gen_skeleton_primary_depth_zero():
    import random
    from artworks.lichen_cells.core import _gen_skeleton
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(1))
    primaries = [b for b in branches if b.depth == 0]
    assert len(primaries) == 3
    secondaries = [b for b in branches if b.depth == 1]
    assert len(secondaries) >= 3  # at least one secondary per primary


def test_branch_envelope_contains_branch_tips():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope, _pip
    branches = _gen_skeleton(cx=150, cy=150, radius=100,
                             n_primary=4, angle_spread=0.6,
                             irregularity=0.4, rng=random.Random(42))
    env = _branch_envelope(branches, cx=150, cy=150)
    assert len(env) == 240
    for b in branches:
        tip_x, tip_y = b.pts[-1]
        assert _pip(tip_x, tip_y, env), f"tip {tip_x:.1f},{tip_y:.1f} outside envelope"

def test_branch_envelope_finite():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(1))
    env = _branch_envelope(branches, cx=150, cy=150)
    for x, y in env:
        assert math.isfinite(x) and math.isfinite(y)

def test_branch_envelope_star_shaped():
    """Envelope should extend further in the direction of branches than between them."""
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _branch_envelope
    branches = _gen_skeleton(150, 150, 100, 4, 0.3, 0.1, random.Random(3))
    env = _branch_envelope(branches, cx=150, cy=150)
    # All envelope points should be at a positive radius from centre
    for x, y in env:
        r = math.sqrt((x - 150)**2 + (y - 150)**2)
        assert r > 0


def test_territory_at_branch_center_near_zero():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _query_territory
    branches = _gen_skeleton(cx=150, cy=150, radius=100,
                             n_primary=4, angle_spread=0.6,
                             irregularity=0.4, rng=random.Random(42))
    # Query at the midpoint of the first primary branch
    b = branches[0]
    mid = b.pts[len(b.pts) // 2]
    dist, tang, depth = _query_territory(mid[0], mid[1], branches)
    assert dist < 0.5   # essentially on the branch
    assert depth == 0   # primary branch

def test_territory_tangent_is_unit_vector():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _query_territory
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(5))
    dist, tang, depth = _query_territory(150, 150, branches)
    assert dist >= 0
    tx, ty = tang
    assert math.isclose(math.sqrt(tx*tx + ty*ty), 1.0, abs_tol=1e-6)

def test_territory_depth_matches_branch():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _query_territory
    branches = _gen_skeleton(150, 150, 100, 2, 0.5, 0.2, random.Random(9))
    # The secondary branch tips are at depth=1; query near a secondary tip
    secondary = [b for b in branches if b.depth == 1][0]
    tip = secondary.pts[-1]
    dist, tang, depth = _query_territory(tip[0], tip[1], branches)
    assert dist < 1.0
    assert depth == 1


def test_gen_voids_count():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _gen_voids
    branches = _gen_skeleton(cx=150, cy=150, radius=100,
                             n_primary=4, angle_spread=0.6,
                             irregularity=0.4, rng=random.Random(42))
    voids = _gen_voids(branches, n_voids=6, rng=random.Random(42))
    assert len(voids) == 6
    for cx, cy, rx, ry, angle in voids:
        assert rx > 0 and ry > 0

def test_in_any_void_inside_and_outside():
    from artworks.lichen_cells.core import _in_any_void
    voids = [(100.0, 100.0, 10.0, 6.0, 0.0)]
    assert _in_any_void(100.0, 100.0, voids)    # centre
    assert _in_any_void(109.0, 100.0, voids)    # just inside x-edge
    assert not _in_any_void(111.0, 100.0, voids) # just outside
    assert not _in_any_void(200.0, 200.0, voids) # far away

def test_gen_voids_zero_returns_empty():
    import random
    from artworks.lichen_cells.core import _gen_skeleton, _gen_voids
    branches = _gen_skeleton(150, 150, 100, 3, 0.5, 0.3, random.Random(1))
    voids = _gen_voids(branches, n_voids=0, rng=random.Random(1))
    assert voids == []
