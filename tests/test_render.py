import re
from engine.types import Path, Canvas
from engine.render import render_svg, render_print_optimized


def test_render_svg_has_mm_viewbox_with_margin():
    c = Canvas(width=200, height=100, margin=2)
    svg = render_svg(c, [])
    assert 'viewBox="0 0 204 104"' in svg
    assert 'width="204mm"' in svg
    assert 'height="104mm"' in svg


def test_render_open_path_is_polyline_offset_by_margin():
    c = Canvas(width=10, height=10, margin=2)
    svg = render_svg(c, [Path(points=[(0, 0), (10, 0)])])
    assert "<polyline" in svg
    assert "2,2" in svg
    assert "12,2" in svg


def test_render_closed_path_is_polygon():
    c = Canvas(width=10, height=10, margin=2)
    svg = render_svg(c, [Path(points=[(0, 0), (10, 0), (5, 8)], closed=True)])
    assert "<polygon" in svg


def test_render_point_is_dot_circle():
    c = Canvas(width=10, height=10, margin=2)
    svg = render_svg(c, [Path(points=[(5, 5)])])
    assert "<circle" in svg
    assert 'cx="7"' in svg
    assert 'cy="7"' in svg


def test_per_path_width_overrides_default():
    c = Canvas(width=10, height=10)
    svg = render_svg(c, [Path(points=[(0, 0), (1, 1)], width=0.8)], default_width=0.5)
    assert 'stroke-width="0.8"' in svg


def test_empty_path_is_skipped():
    c = Canvas(width=10, height=10)
    svg = render_svg(c, [Path(points=[]), Path(points=[(0, 0), (1, 1)])])
    assert svg.count("<polyline") == 1
    assert "<polygon" not in svg


def test_print_optimized_embeds_canvas_size():
    c = Canvas(width=297, height=420)
    svg = render_print_optimized(
        c, [Path(points=[(0, 0), (1, 1)])],
        artwork="demo", seed=1, params={},
    )
    m = re.search(r"<!--\s*(.*?)\s*-->", svg)
    header = m.group(1)
    assert "canvas_width: 297" in header
    assert "canvas_height: 420" in header


def test_metadata_double_dash_is_neutralized():
    c = Canvas(width=10, height=10)
    svg = render_print_optimized(
        c, [Path(points=[(0, 0), (1, 1)])],
        artwork="my--art", seed=1, params={},
    )
    # No literal '--' may remain inside the comment body (illegal in XML).
    m = re.search(r"<!--\s*(.*?)\s*-->", svg)
    assert m is not None
    assert "--" not in m.group(1)


def test_print_optimized_has_white_background_and_thin_stroke():
    c = Canvas(width=10, height=10)
    svg = render_print_optimized(
        c, [Path(points=[(0, 0), (1, 1)])],
        artwork="demo", seed=42, params={"a": 1},
    )
    assert 'fill="white"' in svg
    assert "0.35" in svg


def test_print_optimized_embeds_reproducibility_header():
    c = Canvas(width=10, height=10)
    svg = render_print_optimized(
        c, [Path(points=[(0, 0), (1, 1)])],
        artwork="demo", seed=42, params={"amp": 40, "scale": 0.012},
    )
    m = re.search(r"<!--\s*(.*?)\s*-->", svg)
    assert m is not None
    header = m.group(1)
    assert "artwork: demo" in header
    assert "seed: 42" in header
    assert "amp: 40" in header
    assert "scale: 0.012" in header
