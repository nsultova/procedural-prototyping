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
