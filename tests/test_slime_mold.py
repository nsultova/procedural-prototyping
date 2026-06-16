import random
from engine.types import Canvas
from artworks.slime_mold import core
from artworks.slime_mold.params import PARAMS, PREVIEW


def _params(**overrides):
    p = {p.name: p.default for p in PARAMS}
    # keep the suite fast — exercise behaviour at a lighter food count
    p.update(num_attractors=300, max_steps=300)
    p.update(overrides)
    return p


def test_produces_open_polylines():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _params(), random.Random(42))
    assert len(paths) > 0
    assert all(len(p.points) >= 2 for p in paths)
    assert all(not p.closed for p in paths)


def test_deterministic_for_same_seed():
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


def test_widths_taper_within_bounds():
    canvas = Canvas(width=200, height=200)
    params = _params()
    paths = core.geometry(canvas, params, random.Random(42))
    widths = {p.width for p in paths}
    assert len(widths) > 1                              # actually tapers
    assert min(widths) >= params["min_width"] - 1e-9
    assert max(widths) <= params["max_width"] + 1e-9


def test_preview_overrides_are_lighter():
    from engine.registry import Registry
    reg = Registry()
    assert reg.preview_params("slime_mold")["num_attractors"] < \
        next(p.default for p in PARAMS if p.name == "num_attractors")
    # sanity: the module exposes a PREVIEW dict
    assert "num_attractors" in PREVIEW
