import random
from engine.types import Canvas
from artworks.geological import core
from artworks.geological.params import PARAMS


def _defaults():
    return {p.name: p.default for p in PARAMS}


def test_produces_paths():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _defaults(), random.Random(42))
    assert len(paths) > 0
    assert all(len(p.points) >= 2 for p in paths)


def test_deterministic_for_same_seed():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _defaults(), random.Random(7))
    b = core.geometry(canvas, _defaults(), random.Random(7))
    assert [p.points for p in a] == [p.points for p in b]


def test_points_in_bounds_x():
    # Only X is bounds-checked. Y is intentionally NOT clamped: vertical
    # displacement is meant to bleed strata past the top/bottom edges (the
    # canvas viewBox + plotter margins frame it). This is faithful to the
    # original algorithm, not an oversight — see test_y_may_exceed_bounds.
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _defaults(), random.Random(42))
    for path in paths:
        for x, _y in path.points:
            assert -1e-6 <= x <= canvas.width + 1e-6


def test_y_may_exceed_bounds():
    # Documents intent: at high amplitude, displaced lines deliberately
    # extend beyond the canvas in Y (strata bleeding off the edges).
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["displacement"] = 100
    paths = core.geometry(canvas, params, random.Random(42))
    ys = [y for path in paths for _x, y in path.points]
    assert min(ys) < 0 or max(ys) > canvas.height


def test_stroke_width_applied():
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["stroke_width"] = 0.5
    paths = core.geometry(canvas, params, random.Random(42))
    assert all(p.width == 0.5 for p in paths)


def test_lacunarity_gain_change_output():
    # Confirms the fix: BOTH knobs actually affect geometry now. Each is
    # varied independently (multi-octave defaults) so neither can be silently
    # ignored without this test failing.
    canvas = Canvas(width=200, height=200)
    base = core.geometry(canvas, _defaults(), random.Random(3))

    gain_params = _defaults()
    gain_params["gain"] = 0.7
    gained = core.geometry(canvas, gain_params, random.Random(3))
    assert [p.points for p in base] != [p.points for p in gained]

    lac_params = _defaults()
    lac_params["lacunarity"] = 2.7
    laced = core.geometry(canvas, lac_params, random.Random(3))
    assert [p.points for p in base] != [p.points for p in laced]


def test_degenerate_inputs_do_not_crash():
    # num_lines=1 (denom guard) and x_resolution below the UI min still render.
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["num_lines"] = 1
    params["x_resolution"] = 0  # guarded to >=1 inside geometry
    paths = core.geometry(canvas, params, random.Random(42))
    assert isinstance(paths, list)
