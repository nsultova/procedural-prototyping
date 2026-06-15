import re
from engine.registry import Registry
from engine.types import Canvas
from engine.render import render_print_optimized
from cli import parse_metadata_header, coerce_params


def test_parse_metadata_header_roundtrip():
    reg = Registry()
    canvas = Canvas(width=200, height=200)
    params = reg.merge_params("geological", {"num_lines": 20, "x_resolution": 60})
    svg = render_print_optimized(canvas, [], artwork="geological",
                                 seed=123, params=params)
    parsed = parse_metadata_header(svg)
    assert parsed["artwork"] == "geological"
    assert parsed["seed"] == "123"
    assert parsed["num_lines"] == "20"


def test_coerce_params_casts_using_spec():
    reg = Registry()
    raw = {"num_lines": "20", "noise_scale": "0.012", "x_resolution": "60"}
    coerced = coerce_params(reg, "geological", raw)
    assert coerced["num_lines"] == 20
    assert isinstance(coerced["num_lines"], int)
    assert abs(coerced["noise_scale"] - 0.012) < 1e-9


def test_reproduce_is_deterministic():
    reg = Registry()
    canvas = Canvas(width=200, height=200)
    params = reg.merge_params("geological", {"num_lines": 15, "x_resolution": 50})
    a = reg.render_paths("geological", params, seed=99, canvas=canvas)
    b = reg.render_paths("geological", params, seed=99, canvas=canvas)
    assert [p.points for p in a] == [p.points for p in b]


def test_full_roundtrip_from_exported_svg(tmp_path):
    # End-to-end: export an SVG on a NON-square canvas, then reconstruct
    # everything (artwork, seed, canvas size, params) purely from its header and
    # re-render — the geometry must match the original bit-for-bit. The
    # non-square canvas proves canvas dimensions round-trip (geometry is
    # canvas-size-dependent).
    reg = Registry()
    original_canvas = Canvas(width=297, height=210)
    seed = 77
    original_params = reg.merge_params(
        "geological", {"num_lines": 12, "x_resolution": 40})
    original_paths = reg.render_paths(
        "geological", original_params, seed=seed, canvas=original_canvas)
    svg = render_print_optimized(original_canvas, original_paths,
                                 artwork="geological", seed=seed,
                                 params=original_params)
    svg_file = tmp_path / "exported.svg"
    svg_file.write_text(svg)

    # Reconstruct purely from the file's metadata header — no prior knowledge.
    meta = parse_metadata_header(svg_file.read_text())
    artwork = meta.pop("artwork")
    recovered_seed = int(meta.pop("seed"))
    recovered_canvas = Canvas(width=float(meta.pop("canvas_width")),
                              height=float(meta.pop("canvas_height")))
    recovered_params = coerce_params(reg, artwork, meta)
    recovered_paths = reg.render_paths(
        artwork, recovered_params, seed=recovered_seed, canvas=recovered_canvas)

    assert artwork == "geological"
    assert recovered_seed == seed
    assert (recovered_canvas.width, recovered_canvas.height) == (297, 210)
    assert [p.points for p in recovered_paths] == [p.points for p in original_paths]
