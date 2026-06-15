"""Render a list[Path] to an SVG string (plotter-friendly, millimetre units)."""

from engine.types import Path, Canvas

DOT_RADIUS_MM = 0.15  # rendered radius for point primitives


def _fmt(n: float) -> str:
    """Compact number formatting: trims trailing zeros, avoids '-0'."""
    s = f"{n:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _points_attr(points, ox: float, oy: float) -> str:
    return " ".join(f"{_fmt(x + ox)},{_fmt(y + oy)}" for x, y in points)


def render_svg(
    canvas: Canvas,
    paths: list[Path],
    default_width: float = 0.5,
    background: str | None = None,
    metadata_header: str | None = None,
) -> str:
    """Build an SVG document string from paths.

    - open polyline (closed=False, >=2 pts) -> <polyline>
    - closed polyline (closed=True)         -> <polygon>
    - point (1 pt)                          -> filled <circle> (pen dab)
    """
    ox, oy = canvas.margin, canvas.margin
    vw = canvas.width + 2 * canvas.margin
    vh = canvas.height + 2 * canvas.margin

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{_fmt(vw)}mm" height="{_fmt(vh)}mm" '
        f'viewBox="0 0 {_fmt(vw)} {_fmt(vh)}">'
    ]
    if metadata_header:
        # '--' is illegal inside an XML/SVG comment; keep the doc well-formed.
        out.append(f"<!-- {metadata_header.replace('--', '- -')} -->")
    if background:
        out.append(f'<rect width="100%" height="100%" fill="{background}" />')

    for path in paths:
        if not path.points:
            continue  # nothing to draw; keep the renderer self-defending
        w = path.width if path.width is not None else default_width
        if len(path.points) == 1:
            x, y = path.points[0]
            out.append(
                f'<circle cx="{_fmt(x + ox)}" cy="{_fmt(y + oy)}" '
                f'r="{_fmt(DOT_RADIUS_MM)}" fill="black" />'
            )
        elif path.closed:
            out.append(
                f'<polygon points="{_points_attr(path.points, ox, oy)}" '
                f'fill="none" stroke="black" stroke-width="{_fmt(w)}" />'
            )
        else:
            out.append(
                f'<polyline points="{_points_attr(path.points, ox, oy)}" '
                f'fill="none" stroke="black" stroke-width="{_fmt(w)}" />'
            )

    out.append("</svg>")
    return "\n".join(out)


def _metadata_header(artwork: str, seed: int, params: dict, canvas: Canvas) -> str:
    # Canvas dimensions are part of the recipe: geometry is canvas-size-dependent,
    # so reproduce must restore them too.
    parts = [
        f"artwork: {artwork}",
        f"seed: {seed}",
        f"canvas_width: {canvas.width}",
        f"canvas_height: {canvas.height}",
    ]
    for key, value in params.items():
        parts.append(f"{key}: {value}")
    return " | ".join(parts)


def render_print_optimized(
    canvas: Canvas,
    paths: list[Path],
    artwork: str,
    seed: int,
    params: dict,
    default_width: float = 0.35,
) -> str:
    """Print/plot version: white background, thin default stroke, metadata header."""
    return render_svg(
        canvas,
        paths,
        default_width=default_width,
        background="white",
        metadata_header=_metadata_header(artwork, seed, params, canvas),
    )
