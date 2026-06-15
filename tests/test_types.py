from engine.types import Path, Canvas, Param


def test_canvas_defaults():
    c = Canvas(width=200, height=200)
    assert c.width == 200
    assert c.height == 200
    assert c.margin == 2.0


def test_path_defaults():
    p = Path(points=[(0, 0), (1, 1)])
    assert p.points == [(0, 0), (1, 1)]
    assert p.closed is False
    assert p.width is None


def test_path_point_is_single_coordinate():
    dot = Path(points=[(5, 5)])
    assert len(dot.points) == 1


def test_param_to_dict_roundtrip():
    param = Param("amp", "Amplitude (mm)", 0, 100, 1, 40, group="Displacement")
    d = param.to_dict()
    assert d == {
        "name": "amp",
        "label": "Amplitude (mm)",
        "min": 0,
        "max": 100,
        "step": 1,
        "default": 40,
        "group": "Displacement",
    }


def test_param_default_group():
    param = Param("x", "X", 0, 1, 0.1, 0.5)
    assert param.group == "General"
