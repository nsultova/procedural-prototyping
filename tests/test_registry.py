import pytest
from engine.registry import Registry
from engine.types import Canvas


@pytest.fixture
def reg():
    return Registry(package="tests", folder="tests")


def test_discovers_fixture_artwork(reg):
    names = reg.names()
    assert "_fixture_artwork" in names


def test_spec_returns_title_and_params(reg):
    spec = reg.spec("_fixture_artwork")
    assert spec["title"] == "Fixture"
    assert spec["subtitle"] == "test artwork"
    assert [p["name"] for p in spec["params"]] == ["count", "size"]


def test_merge_fills_missing_params_with_defaults(reg):
    merged = reg.merge_params("_fixture_artwork", {"count": 5})
    assert merged == {"count": 5, "size": 20}


def test_merge_ignores_unknown_keys(reg):
    merged = reg.merge_params("_fixture_artwork", {"count": 5, "bogus": 99})
    assert "bogus" not in merged


def test_preview_params_empty_when_artwork_declares_none(reg):
    # The fixture artwork has no PREVIEW, so preview renders == full renders.
    assert reg.preview_params("_fixture_artwork") == {}


def test_render_returns_paths(reg):
    canvas = Canvas(width=100, height=100)
    paths = reg.render_paths("_fixture_artwork", {"count": 4}, seed=42, canvas=canvas)
    assert len(paths) == 4


def test_render_is_deterministic(reg):
    canvas = Canvas(width=100, height=100)
    a = reg.render_paths("_fixture_artwork", {"count": 3}, seed=1, canvas=canvas)
    b = reg.render_paths("_fixture_artwork", {"count": 3}, seed=1, canvas=canvas)
    assert [p.points for p in a] == [p.points for p in b]


def test_unknown_artwork_raises(reg):
    with pytest.raises(KeyError):
        reg.spec("does_not_exist")


def test_spec_validation_rejects_default_out_of_range():
    from engine.types import Param
    from engine.registry import validate_params
    bad = [Param("x", "X", 0, 10, 1, 50)]  # default 50 > max 10
    with pytest.raises(ValueError):
        validate_params("broken", bad)


def test_spec_validation_rejects_duplicate_names():
    from engine.types import Param
    from engine.registry import validate_params
    bad = [Param("x", "X", 0, 10, 1, 5), Param("x", "X again", 0, 10, 1, 5)]
    with pytest.raises(ValueError):
        validate_params("broken", bad)


def test_spec_validation_rejects_nonpositive_step():
    from engine.types import Param
    from engine.registry import validate_params
    bad = [Param("x", "X", 0, 10, 0, 5)]  # step 0 is invalid
    with pytest.raises(ValueError):
        validate_params("broken", bad)
