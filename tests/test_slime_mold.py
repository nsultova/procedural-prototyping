import random
from engine.types import Canvas
from artworks.slime_mold import core
from artworks.slime_mold.params import PARAMS, PREVIEW


def _params(**overrides):
    p = {p.name: p.default for p in PARAMS}
    # keep the suite fast — lighter growth than the live defaults
    p.update(num_attractors=250, max_steps=250)
    p.update(overrides)
    return p


def test_produces_open_polylines():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(), random.Random(42))
    assert len(paths) > 0
    assert all(len(p.points) >= 2 for p in paths)
    assert all(not p.closed for p in paths)


def test_deterministic_with_all_layers():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _params(), random.Random(11))
    b = core.geometry(canvas, _params(), random.Random(11))
    assert [p.points for p in a] == [p.points for p in b]


def test_different_seed_changes_output():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _params(), random.Random(1))
    b = core.geometry(canvas, _params(), random.Random(2))
    assert [p.points for p in a] != [p.points for p in b]


def test_points_in_bounds():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(), random.Random(42))
    for path in paths:
        for x, y in path.points:
            assert -1e-6 <= x <= canvas.width + 1e-6
            assert -1e-6 <= y <= canvas.height + 1e-6


def test_bare_veins_when_mesh_off():
    # mesh_density=0 -> only the tapered vein strands remain.
    canvas = Canvas(width=200, height=200)
    bare = core.geometry(canvas, _params(mesh_density=0), random.Random(42))
    full = core.geometry(canvas, _params(), random.Random(42))
    assert len(full) > len(bare)
    # veins still taper (more than one distinct width) even when bare
    assert len({p.width for p in bare}) > 1


def test_mesh_adds_links():
    canvas = Canvas(width=200, height=200)
    no_mesh = core.geometry(canvas, _params(mesh_density=0), random.Random(42))
    meshed = core.geometry(canvas, _params(mesh_density=0.6), random.Random(42))
    assert len(meshed) > len(no_mesh)


def test_widths_within_bounds():
    canvas = Canvas(width=200, height=200)
    params = _params()
    paths = core.geometry(canvas, params, random.Random(42))
    widths = {p.width for p in paths}
    assert min(widths) >= params["min_width"] - 1e-9
    assert max(widths) <= params["max_width"] + 1e-9


def test_preview_overrides_are_lighter():
    from engine.registry import Registry
    reg = Registry()
    prev = reg.preview_params("slime_mold")
    assert prev["num_attractors"] < next(p.default for p in PARAMS if p.name == "num_attractors")
    assert "num_attractors" in PREVIEW
