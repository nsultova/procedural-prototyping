import random
from engine.types import Canvas
from artworks.water_droplets import core
from artworks.water_droplets.params import PARAMS


def _defaults():
    return {p.name: p.default for p in PARAMS}


def test_produces_closed_paths():
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _defaults(), random.Random(42))
    assert len(paths) > 0
    # Every droplet primitive (ripple ring, impact ring, secondary ring) is a
    # closed polyline — the renderer needs no separate circle primitive.
    assert all(p.closed for p in paths)


def test_deterministic_for_same_seed():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _defaults(), random.Random(11))
    b = core.geometry(canvas, _defaults(), random.Random(11))
    assert [p.points for p in a] == [p.points for p in b]


def test_different_seed_changes_layout():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _defaults(), random.Random(1))
    b = core.geometry(canvas, _defaults(), random.Random(2))
    assert [p.points for p in a] != [p.points for p in b]


def test_ring_points_controls_resolution():
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["ring_points"] = 80
    paths = core.geometry(canvas, params, random.Random(42))
    ripple_lengths = {len(p.points) for p in paths}
    assert 80 in ripple_lengths


def test_single_drop_has_no_interference_and_renders():
    # num_drops=1: the cross-drop interference loop never runs (no "other").
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["num_drops"] = 1
    paths = core.geometry(canvas, params, random.Random(42))
    assert len(paths) > 0


def test_degenerate_wavelength_does_not_crash():
    # interference_wavelength_factor=0 (below UI min) would zero the wavelength;
    # the guard must keep the multi-drop interference term from dividing by zero.
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["num_drops"] = 3
    params["interference_wavelength_factor"] = 0
    paths = core.geometry(canvas, params, random.Random(42))
    assert len(paths) > 0


def test_only_ripple_rings_when_extras_disabled():
    # secondary_drops=0 and impact_rings=0 -> output is purely ripple rings.
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["secondary_drops"] = 0
    params["impact_rings"] = 0
    params["ring_points"] = 64
    paths = core.geometry(canvas, params, random.Random(42))
    assert len(paths) > 0
    assert all(len(p.points) == 64 for p in paths)
