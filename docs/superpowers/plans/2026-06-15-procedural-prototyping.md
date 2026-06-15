# Procedural Prototyping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible pen-plotter art workbench where each artwork is a pure `geometry(canvas, params, rng) -> list[Path]` function that drives both a generic live web UI and plotter-ready A3 SVG export, with `geological` and `water_droplets` ported as the first two artworks.

**Architecture:** A small `engine/` defines the data types, an SVG renderer, and an artwork registry. Each `artworks/<name>/` folder contains a pure `core.py` (geometry) and `params.py` (declarative slider spec) — the single source of truth. A Flask server (`server/app.py`) exposes the registry, per-artwork param specs, and a render endpoint; one generic data-driven HTML shell builds sliders from the spec and shows live SVG. A `cli.py` provides `serve`, `list`, `batch`, and `reproduce`. The live preview and the export run the identical code path, so the preview is exactly what plots.

**Tech Stack:** Python 3.10+, Flask, pytest. No svgwrite/numpy needed — the renderer emits SVG strings directly and the ported algorithms are pure-Python math.

---

## File Structure

```
procedural-prototyping/
  engine/
    __init__.py
    types.py        # Path, Canvas, Param dataclasses
    render.py       # list[Path] -> SVG string (standard + print-optimized + metadata header)
    registry.py     # discover + validate artworks/, merge params with spec defaults
  artworks/
    __init__.py
    geological/
      __init__.py
      core.py       # geometry() + noise helpers (open polylines)
      params.py     # TITLE, SUBTITLE, PARAMS
    water_droplets/
      __init__.py
      core.py       # geometry() (closed polylines)
      params.py     # TITLE, SUBTITLE, PARAMS
  server/
    __init__.py
    app.py          # Flask app factory + routes
    static/
      index.html    # generic UI shell
      app.js        # data-driven sliders + render loop + pan/zoom + export
      style.css     # dark panel aesthetic
  tests/
    test_types.py
    test_render.py
    test_registry.py
    test_geological.py
    test_water_droplets.py
    test_server.py
    test_reproduce.py
    _fixture_artwork/   # minimal artwork used by registry tests
      __init__.py
      core.py
      params.py
  cli.py
  pyproject.toml
  requirements.txt
  .gitignore
  output/
    drafts/.gitkeep
    keepers/.gitkeep
```

Conventions used by every artwork:
- `core.geometry(canvas: Canvas, p: dict, rng: random.Random) -> list[Path]` — pure, no global state, no I/O.
- `p` is guaranteed by the registry to contain **every** name in `PARAMS` (incoming values merged over spec defaults), so `core.py` reads `p["name"]` directly (never `p.get`).
- Coordinates are in millimetres, origin top-left, within `[0, canvas.width] x [0, canvas.height]`.

---

## Task 1: Project scaffolding, packaging, and core types

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `engine/__init__.py` (empty)
- Create: `artworks/__init__.py` (empty)
- Create: `server/__init__.py` (empty)
- Create: `output/drafts/.gitkeep`, `output/keepers/.gitkeep` (empty)
- Create: `engine/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Create `requirements.txt`**

```
flask>=3.0
pytest>=7.0
```

- [ ] **Step 2: Create `pyproject.toml`** (makes `pytest` find packages from repo root)

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
output/drafts/*
output/keepers/*
!output/drafts/.gitkeep
!output/keepers/.gitkeep
```

- [ ] **Step 4: Create empty package files**

Create empty `engine/__init__.py`, `artworks/__init__.py`, `server/__init__.py`, `output/drafts/.gitkeep`, `output/keepers/.gitkeep`.

- [ ] **Step 5: Write the failing test** — `tests/test_types.py`

```python
import math
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
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_types.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.types'`

- [ ] **Step 7: Write `engine/types.py`**

```python
"""Core data types shared by the engine, artworks, and renderer."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Canvas:
    """Drawing surface in millimetres."""
    width: float
    height: float
    margin: float = 2.0  # viewBox margin in mm


@dataclass
class Path:
    """The single output primitive for all artworks.

    Three forms, all plotter-native:
      - open polyline : len(points) >= 2, closed=False
      - closed polyline: closed=True
      - point / dot    : len(points) == 1
    """
    points: list                 # list[tuple[float, float]] in mm
    closed: bool = False
    width: float | None = None   # stroke width in mm; None -> renderer default


@dataclass
class Param:
    """Declarative slider specification for one algorithm knob."""
    name: str
    label: str
    min: float
    max: float
    step: float
    default: float
    group: str = "General"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "min": self.min,
            "max": self.max,
            "step": self.step,
            "default": self.default,
            "group": self.group,
        }
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_types.py -v`
Expected: PASS (5 passed)

- [ ] **Step 9: Commit**

```bash
git add requirements.txt pyproject.toml .gitignore engine artworks server output tests/test_types.py
git commit -m "feat: project scaffolding and core types (Path, Canvas, Param)"
```

---

## Task 2: SVG renderer

The renderer turns `list[Path]` into an SVG string. It produces a standard preview SVG and a print-optimized SVG (white background, thinner default stroke, and a metadata comment that records artwork + seed + params for reproducibility).

**Files:**
- Create: `engine/render.py`
- Test: `tests/test_render.py`

- [ ] **Step 1: Write the failing test** — `tests/test_render.py`

```python
import re
from engine.types import Path, Canvas
from engine.render import render_svg, render_print_optimized


def test_render_svg_has_mm_viewbox_with_margin():
    c = Canvas(width=200, height=100, margin=2)
    svg = render_svg(c, [])
    # viewBox = width+2*margin  height+2*margin
    assert 'viewBox="0 0 204 104"' in svg
    assert 'width="204mm"' in svg
    assert 'height="104mm"' in svg


def test_render_open_path_is_polyline_offset_by_margin():
    c = Canvas(width=10, height=10, margin=2)
    svg = render_svg(c, [Path(points=[(0, 0), (10, 0)])])
    assert "<polyline" in svg
    # points are offset by the margin (2,2)
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
    assert 'cx="7"' in svg  # 5 + margin 2
    assert 'cy="7"' in svg


def test_per_path_width_overrides_default():
    c = Canvas(width=10, height=10)
    svg = render_svg(c, [Path(points=[(0, 0), (1, 1)], width=0.8)], default_width=0.5)
    assert "0.8" in svg


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.render'`

- [ ] **Step 3: Write `engine/render.py`**

```python
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
        out.append(f"<!-- {metadata_header} -->")
    if background:
        out.append(f'<rect width="100%" height="100%" fill="{background}" />')

    for path in paths:
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


def _metadata_header(artwork: str, seed: int, params: dict) -> str:
    parts = [f"artwork: {artwork}", f"seed: {seed}"]
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
        metadata_header=_metadata_header(artwork, seed, params),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_render.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add engine/render.py tests/test_render.py
git commit -m "feat: SVG renderer with standard + print-optimized output and metadata header"
```

---

## Task 3: Artwork registry

The registry discovers artwork packages under `artworks/`, validates each one's spec, and provides param-merging (incoming values over spec defaults) plus a render helper used by both the server and the CLI.

**Files:**
- Create: `engine/registry.py`
- Create: `tests/_fixture_artwork/__init__.py` (empty)
- Create: `tests/_fixture_artwork/params.py`
- Create: `tests/_fixture_artwork/core.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Create the fixture artwork** — `tests/_fixture_artwork/params.py`

```python
from engine.types import Param

TITLE = "Fixture"
SUBTITLE = "test artwork"

PARAMS = [
    Param("count", "Count", 1, 10, 1, 3, group="Main"),
    Param("size", "Size (mm)", 1, 100, 1, 20, group="Main"),
]
```

- [ ] **Step 2: Create the fixture core** — `tests/_fixture_artwork/core.py`

```python
from engine.types import Path, Canvas


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    paths = []
    for i in range(int(p["count"])):
        y = (i + 1) / (p["count"] + 1) * canvas.height
        paths.append(Path(points=[(0, y), (p["size"], y)]))
    return paths
```

Create empty `tests/_fixture_artwork/__init__.py`.

- [ ] **Step 3: Write the failing test** — `tests/test_registry.py`

```python
import pytest
from engine.registry import Registry
from engine.types import Canvas


@pytest.fixture
def reg():
    # Point the registry at the tests package so it picks up _fixture_artwork
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.registry'`

- [ ] **Step 5: Write `engine/registry.py`**

```python
"""Discover, validate, and run artwork packages."""

import importlib
import pkgutil
import random
from pathlib import Path as FsPath

from engine.types import Canvas, Param


def validate_params(artwork: str, params: list[Param]) -> None:
    """Raise ValueError if any Param is malformed."""
    seen = set()
    for p in params:
        if p.name in seen:
            raise ValueError(f"{artwork}: duplicate param '{p.name}'")
        seen.add(p.name)
        if not (p.min <= p.default <= p.max):
            raise ValueError(
                f"{artwork}: param '{p.name}' default {p.default} "
                f"outside [{p.min}, {p.max}]"
            )
        if p.step <= 0:
            raise ValueError(f"{artwork}: param '{p.name}' step must be > 0")


class Registry:
    """Loads artwork packages of the form <package>.<name> with core+params."""

    def __init__(self, package: str = "artworks", folder: str = "artworks"):
        self._package = package
        self._folder = folder
        self._cache: dict = {}
        self._discover()

    def _discover(self) -> None:
        base = FsPath(self._folder)
        for mod in pkgutil.iter_modules([str(base)]):
            name = mod.name
            if name.startswith("__"):
                continue
            try:
                params_mod = importlib.import_module(f"{self._package}.{name}.params")
                core_mod = importlib.import_module(f"{self._package}.{name}.core")
            except ModuleNotFoundError:
                continue
            if not hasattr(params_mod, "PARAMS") or not hasattr(core_mod, "geometry"):
                continue
            validate_params(name, params_mod.PARAMS)
            self._cache[name] = (core_mod, params_mod)

    def names(self) -> list[str]:
        return sorted(self._cache.keys())

    def _get(self, name: str):
        if name not in self._cache:
            raise KeyError(f"unknown artwork: {name}")
        return self._cache[name]

    def spec(self, name: str) -> dict:
        _core, params_mod = self._get(name)
        return {
            "name": name,
            "title": getattr(params_mod, "TITLE", name),
            "subtitle": getattr(params_mod, "SUBTITLE", ""),
            "params": [p.to_dict() for p in params_mod.PARAMS],
        }

    def defaults(self, name: str) -> dict:
        _core, params_mod = self._get(name)
        return {p.name: p.default for p in params_mod.PARAMS}

    def merge_params(self, name: str, incoming: dict) -> dict:
        """Incoming values over spec defaults; unknown keys dropped."""
        merged = self.defaults(name)
        for key, value in incoming.items():
            if key in merged:
                merged[key] = value
        return merged

    def render_paths(self, name: str, params: dict, seed: int, canvas: Canvas) -> list:
        core_mod, _params_mod = self._get(name)
        merged = self.merge_params(name, params)
        rng = random.Random(seed)
        return core_mod.geometry(canvas, merged, rng)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_registry.py -v`
Expected: PASS (8 passed)

- [ ] **Step 7: Commit**

```bash
git add engine/registry.py tests/_fixture_artwork tests/test_registry.py
git commit -m "feat: artwork registry with discovery, spec validation, and param merging"
```

---

## Task 4: Port the `geological` artwork

Faithful port of `geological_strata.py` to a pure geometry function. Notable fix: `lacunarity` and `gain` are now actually threaded into `fbm` (the original Python stored but never used them; the HTML did use them), so those sliders work.

**Files:**
- Create: `artworks/geological/__init__.py` (empty)
- Create: `artworks/geological/params.py`
- Create: `artworks/geological/core.py`
- Test: `tests/test_geological.py`

- [ ] **Step 1: Create `artworks/geological/__init__.py`** (empty)

- [ ] **Step 2: Create `artworks/geological/params.py`**

```python
from engine.types import Param

TITLE = "Geological Strata"
SUBTITLE = "displaced line field · domain-warped noise terrain"

PARAMS = [
    # Line field
    Param("num_lines",     "Line count",     1,    400,  1,     200,   group="Line field"),
    Param("x_resolution",  "X resolution",   50,   600,  10,    300,   group="Line field"),
    # Displacement
    Param("displacement",  "Amplitude (mm)", 5,    100,  1,     40,    group="Displacement"),
    Param("noise_scale",   "Noise scale",    0.002, 0.05, 0.001, 0.012, group="Displacement"),
    Param("octaves",       "Octaves",        1,    8,    1,     6,     group="Displacement"),
    Param("lacunarity",    "Lacunarity",     1.5,  3.0,  0.1,   2.0,   group="Displacement"),
    Param("gain",          "Gain",           0.3,  0.7,  0.05,  0.5,   group="Displacement"),
    # Domain warping
    Param("warp_strength", "Warp strength",  0.0,  8.0,  0.1,   2.5,   group="Domain warping"),
    Param("warp_scale",    "Warp scale",     0.002, 0.04, 0.001, 0.008, group="Domain warping"),
    Param("warp_octaves",  "Warp octaves",   1,    6,    1,     3,     group="Domain warping"),
    # Boundary
    Param("edge_roughness","Edge roughness", 0.0,  1.0,  0.05,  0.7,   group="Boundary"),
    Param("edge_scale",    "Edge noise scale",0.005, 0.06, 0.001, 0.02, group="Boundary"),
    Param("edge_inset",    "Edge inset",     0.0,  0.2,  0.01,  0.05,  group="Boundary"),
    # Style
    Param("stroke_width",  "Stroke width",   0.1,  1.0,  0.05,  0.35,  group="Style"),
]
```

- [ ] **Step 3: Create `artworks/geological/core.py`**

```python
"""Geological Strata — densely packed scanlines displaced by domain-warped fBm.

Pure port of the original geological_strata.py. Fix vs. original Python:
lacunarity & gain are now threaded into fbm so those knobs take effect
(the original stored them but never passed them through).
"""

import math

from engine.types import Path, Canvas

_GRADS = [(math.cos(a), math.sin(a)) for a in
          (math.pi * 2 * i / 12 for i in range(12))]


def _build_perm(seed: int) -> list:
    import random
    rng = random.Random(seed)
    p = list(range(256))
    rng.shuffle(p)
    return p + p


def _noise2(x: float, y: float, perm: list) -> float:
    xi = int(math.floor(x)) & 255
    yi = int(math.floor(y)) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    u = xf * xf * xf * (xf * (xf * 6.0 - 15.0) + 10.0)
    v = yf * yf * yf * (yf * (yf * 6.0 - 15.0) + 10.0)
    aa = perm[perm[xi] + yi] % 12
    ab = perm[perm[xi] + yi + 1] % 12
    ba = perm[perm[xi + 1] + yi] % 12
    bb = perm[perm[xi + 1] + yi + 1] % 12

    def dot(gi, fx, fy):
        g = _GRADS[gi]
        return g[0] * fx + g[1] * fy

    x1 = dot(aa, xf, yf) + u * (dot(ba, xf - 1, yf) - dot(aa, xf, yf))
    x2 = dot(ab, xf, yf - 1) + u * (dot(bb, xf - 1, yf - 1) - dot(ab, xf, yf - 1))
    return x1 + v * (x2 - x1)


def _fbm(x, y, perm, octaves, lacunarity, gain):
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0
    for _ in range(int(octaves)):
        total += _noise2(x * frequency, y * frequency, perm) * amplitude
        max_amp += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / max_amp if max_amp else 0.0


def _warped_fbm(x, y, perm, perm2, octaves, warp_strength, warp_scale,
                warp_octaves, lacunarity, gain):
    wx = _fbm(x * warp_scale, y * warp_scale, perm2, warp_octaves, lacunarity, gain) * warp_strength
    wy = _fbm(x * warp_scale + 5.2, y * warp_scale + 1.3, perm2, warp_octaves, lacunarity, gain) * warp_strength
    return _fbm(x + wx, y + wy, perm, octaves, lacunarity, gain)


def _edge_mask(x, y, perm, W, H, edge_inset, edge_roughness, edge_scale):
    inset = edge_inset
    dl = x / (W * inset + 1e-6)
    dr = (W - x) / (W * inset + 1e-6)
    dt = y / (H * inset + 1e-6)
    db = (H - y) / (H * inset + 1e-6)
    d = min(dl, dr, dt, db)
    if edge_roughness > 0:
        nv = _fbm(x * edge_scale, y * edge_scale, perm, 3, 2.0, 0.5)
        d += nv * edge_roughness * 0.8
    return max(0.0, min(1.0, d))


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    num_lines = int(p["num_lines"])
    x_res = int(p["x_resolution"])
    noise_scale = p["noise_scale"]
    octaves = int(p["octaves"])
    lacunarity = p["lacunarity"]
    gain = p["gain"]
    warp_strength = p["warp_strength"]
    rel_warp_scale = p["warp_scale"] / max(noise_scale, 1e-6)
    warp_octaves = int(p["warp_octaves"])
    displacement = p["displacement"]
    edge_inset = p["edge_inset"]
    edge_roughness = p["edge_roughness"]
    edge_scale = p["edge_scale"]
    stroke_width = p["stroke_width"]

    # Permutation tables derived from the global seed via rng
    base_seed = rng.randint(0, 2**31 - 1)
    perm = _build_perm(base_seed)
    perm2 = _build_perm(base_seed + 12345)
    perm_edge = _build_perm(base_seed + 67890)

    paths: list[Path] = []
    denom = max(num_lines - 1, 1)
    for li in range(num_lines):
        base_y = (li / denom) * H
        points = []
        for xi in range(x_res + 1):
            x = (xi / x_res) * W
            disp = _warped_fbm(
                x * noise_scale, base_y * noise_scale,
                perm, perm2, octaves, warp_strength, rel_warp_scale,
                warp_octaves, lacunarity, gain,
            )
            y_disp = base_y + disp * displacement
            mask = _edge_mask(x, base_y, perm_edge, W, H,
                              edge_inset, edge_roughness, edge_scale)
            if mask < 0.01:
                if len(points) >= 2:
                    paths.append(Path(points=points, width=stroke_width))
                points = []
                continue
            points.append((x, y_disp))
        if len(points) >= 2:
            paths.append(Path(points=points, width=stroke_width))
    return paths
```

- [ ] **Step 4: Write the failing test** — `tests/test_geological.py`

```python
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
    canvas = Canvas(width=200, height=200)
    paths = core.geometry(canvas, _defaults(), random.Random(42))
    for path in paths:
        for x, _y in path.points:
            assert -1e-6 <= x <= canvas.width + 1e-6


def test_stroke_width_applied():
    canvas = Canvas(width=200, height=200)
    params = _defaults()
    params["stroke_width"] = 0.5
    paths = core.geometry(canvas, params, random.Random(42))
    assert all(p.width == 0.5 for p in paths)


def test_lacunarity_gain_change_output():
    # Confirms the fix: these knobs actually affect geometry now.
    canvas = Canvas(width=200, height=200)
    base = core.geometry(canvas, _defaults(), random.Random(3))
    tweaked_params = _defaults()
    tweaked_params["gain"] = 0.7
    tweaked = core.geometry(canvas, tweaked_params, random.Random(3))
    assert [p.points for p in base] != [p.points for p in tweaked]
```

- [ ] **Step 5: Run test to verify it fails first, then implementation already exists**

Run: `pytest tests/test_geological.py -v`
Expected: PASS (5 passed). (Implementation written in Step 3; if any test fails, fix `core.py` before committing.)

- [ ] **Step 6: Commit**

```bash
git add artworks/geological tests/test_geological.py
git commit -m "feat: port geological strata to pure geometry core (lacunarity/gain fixed)"
```

---

## Task 5: Port the `water_droplets` artwork

Faithful port of `water_droplets.py`. The original tuple `distortion_freqs=(3,7,13)` is exposed as three integer sliders `freq1/freq2/freq3`. The original `add_circle` calls (impact rings, perfect secondary rings) become point-sampled **closed polylines** so the renderer needs only polylines. Rarely-touched secondary knobs (`secondary_dist_min/max`, `secondary_distortion`, `secondary_dist_freq`, `secondary_dist_growth`) are kept as module constants to keep the slider count reasonable.

**Files:**
- Create: `artworks/water_droplets/__init__.py` (empty)
- Create: `artworks/water_droplets/params.py`
- Create: `artworks/water_droplets/core.py`
- Test: `tests/test_water_droplets.py`

- [ ] **Step 1: Create `artworks/water_droplets/__init__.py`** (empty)

- [ ] **Step 2: Create `artworks/water_droplets/params.py`**

```python
from engine.types import Param

TITLE = "Water Droplets"
SUBTITLE = "generative plotter art · ripple interference"

PARAMS = [
    # Drops
    Param("num_drops",  "Number of drops", 1, 10, 1, 4,  group="Drops"),
    Param("max_rings",  "Max rings / drop", 2, 20, 1, 11, group="Drops"),
    # Ring geometry
    Param("ring_spacing",        "Inner spacing (mm)", 1.0, 10.0, 0.5,  4.0,  group="Ring geometry"),
    Param("ring_spacing_growth", "Spacing growth",     1.0, 1.5,  0.01, 1.11, group="Ring geometry"),
    # Distortion
    Param("distortion",        "Amplitude (mm)", 0.0, 5.0, 0.1,  1.4,  group="Distortion"),
    Param("freq1",             "Frequency 1",    1,   20,  1,    3,    group="Distortion"),
    Param("freq2",             "Frequency 2",    1,   20,  1,    7,    group="Distortion"),
    Param("freq3",             "Frequency 3",    1,   20,  1,    13,   group="Distortion"),
    Param("distortion_growth", "Growth / ring",  0.0, 0.3, 0.01, 0.05, group="Distortion"),
    # Wave interference
    Param("interference_strength",          "Strength (mm)", 0.0, 3.0, 0.05, 0.65, group="Wave interference"),
    Param("interference_wavelength_factor", "Wavelength ×",  0.5, 5.0, 0.1,  2.4,  group="Wave interference"),
    # Secondary drops
    Param("secondary_drops",        "Count",         0,   15,  1,   5,   group="Secondary drops"),
    Param("secondary_rings",        "Rings",         0,   8,   1,   3,   group="Secondary drops"),
    Param("secondary_ring_spacing", "Spacing (mm)",  0.2, 3.0, 0.1, 0.9, group="Secondary drops"),
    # Impact center
    Param("impact_rings",        "Impact rings",   0,   8,   1,    3,    group="Impact"),
    Param("impact_ring_spacing", "Impact spacing", 0.05, 1.0, 0.01, 0.22, group="Impact"),
    # Style
    Param("ring_points",  "Ring resolution", 32, 400, 8,    200,  group="Style"),
    Param("stroke_width", "Stroke width",    0.1, 1.0, 0.05, 0.35, group="Style"),
]
```

- [ ] **Step 3: Create `artworks/water_droplets/core.py`**

```python
"""Water Droplets — concentric distorted ripple rings with cross-drop interference.

Pure port of water_droplets.py. Circles become point-sampled closed polylines
so the renderer only needs polylines. Random draws use the passed-in rng.
"""

import math

from engine.types import Path, Canvas

# Rarely-touched secondary knobs kept as constants (defaults from the original).
SECONDARY_DIST_MIN = 0.7
SECONDARY_DIST_MAX = 1.4
SECONDARY_DISTORTION = 0.0
SECONDARY_DIST_FREQ = 5
SECONDARY_DIST_GROWTH = 0.1


def _circle(cx, cy, r, n, width):
    pts = []
    for k in range(n):
        theta = 2 * math.pi * k / n
        pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return Path(points=pts, closed=True, width=width)


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    num_drops = int(p["num_drops"])
    max_rings = int(p["max_rings"])
    ring_spacing = p["ring_spacing"]
    ring_spacing_growth = p["ring_spacing_growth"]
    distortion = p["distortion"]
    freqs = [int(p["freq1"]), int(p["freq2"]), int(p["freq3"])]
    distortion_growth = p["distortion_growth"]
    interference_strength = p["interference_strength"]
    interference_wavelength_factor = p["interference_wavelength_factor"]
    secondary_drops = int(p["secondary_drops"])
    secondary_rings = int(p["secondary_rings"])
    secondary_ring_spacing = p["secondary_ring_spacing"]
    impact_rings = int(p["impact_rings"])
    impact_ring_spacing = p["impact_ring_spacing"]
    ring_points = int(p["ring_points"])
    stroke_width = p["stroke_width"]
    n_freqs = len(freqs)

    paths: list[Path] = []

    # Build drops (order of rng draws preserved from the original)
    drops = []
    for _ in range(num_drops):
        x = rng.uniform(W * 0.15, W * 0.85)
        y = rng.uniform(H * 0.15, H * 0.85)
        age = rng.uniform(0.4, 1.0)
        phases = [rng.uniform(0, 2 * math.pi) for _ in freqs]
        drops.append({"x": x, "y": y, "age": age, "phases": phases})

    wavelength = ring_spacing * interference_wavelength_factor

    for drop in drops:
        cx, cy = drop["x"], drop["y"]
        n_rings = max(2, int(max_rings * drop["age"]))

        # Ripple rings
        for ring_idx in range(n_rings):
            base_r = ring_spacing * (ring_spacing_growth ** ring_idx)
            dist_amp = distortion * (1.0 + distortion_growth * ring_idx)
            pts = []
            for i in range(ring_points):
                theta = 2 * math.pi * i / ring_points
                r = base_r
                for freq, phase in zip(freqs, drop["phases"]):
                    r += (dist_amp / n_freqs) * math.sin(freq * theta + phase)
                px = cx + base_r * math.cos(theta)
                py = cy + base_r * math.sin(theta)
                for other in drops:
                    if other is drop:
                        continue
                    dx = px - other["x"]
                    dy = py - other["y"]
                    dist = math.sqrt(dx * dx + dy * dy)
                    r += interference_strength * math.cos(2 * math.pi * dist / wavelength)
                pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
            paths.append(Path(points=pts, closed=True, width=stroke_width))

        # Impact center
        gap = ring_spacing * impact_ring_spacing
        for i in range(1, impact_rings + 1):
            paths.append(_circle(cx, cy, i * gap, max(24, ring_points // 4), stroke_width))

        # Secondary micro-splashes
        for _ in range(secondary_drops):
            angle = rng.uniform(0, 2 * math.pi)
            dist = rng.uniform(
                ring_spacing * SECONDARY_DIST_MIN,
                ring_spacing * 2 + SECONDARY_DIST_MAX * 8,
            )
            sx = cx + dist * math.cos(angle)
            sy = cy + dist * math.sin(angle)
            if not (0 <= sx <= W and 0 <= sy <= H):
                continue
            ph0 = rng.uniform(0, 2 * math.pi)
            ph1 = rng.uniform(0, 2 * math.pi)
            for j in range(1, secondary_rings + 1):
                base_r = j * secondary_ring_spacing
                dist_amp = SECONDARY_DISTORTION * (1 + SECONDARY_DIST_GROWTH * (j - 1))
                if dist_amp <= 0:
                    paths.append(_circle(sx, sy, base_r, max(24, ring_points // 4), stroke_width))
                else:
                    n_pts = max(32, int(ring_points * 0.35))
                    pts = []
                    for k in range(n_pts):
                        theta = 2 * math.pi * k / n_pts
                        r = base_r
                        r += dist_amp * math.sin(SECONDARY_DIST_FREQ * theta + ph0)
                        r += dist_amp * 0.4 * math.sin(SECONDARY_DIST_FREQ * 2.1 * theta + ph1)
                        pts.append((sx + r * math.cos(theta), sy + r * math.sin(theta)))
                    paths.append(Path(points=pts, closed=True, width=stroke_width))

    return paths
```

- [ ] **Step 4: Write the failing test** — `tests/test_water_droplets.py`

```python
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
    assert any(p.closed for p in paths)


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
    # The main ripple rings should have exactly ring_points vertices
    ripple_lengths = {len(p.points) for p in paths}
    assert 80 in ripple_lengths
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_water_droplets.py -v`
Expected: PASS (4 passed). Fix `core.py` if any fail before committing.

- [ ] **Step 6: Commit**

```bash
git add artworks/water_droplets tests/test_water_droplets.py
git commit -m "feat: port water droplets to pure geometry core (rings as closed polylines)"
```

---

## Task 6: Flask server

Exposes the registry, per-artwork specs, and a render endpoint. The render endpoint returns the standard SVG plus timing; errors in `geometry()` come back as JSON so the UI can show them.

**Files:**
- Create: `server/app.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test** — `tests/test_server.py`

```python
import json
import pytest
from server.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"<html" in r.data.lower()


def test_artworks_lists_both(client):
    r = client.get("/api/artworks")
    assert r.status_code == 200
    names = [a["name"] for a in r.get_json()]
    assert "geological" in names
    assert "water_droplets" in names


def test_spec_returns_params(client):
    r = client.get("/api/spec/geological")
    assert r.status_code == 200
    spec = r.get_json()
    assert spec["title"] == "Geological Strata"
    assert any(p["name"] == "num_lines" for p in spec["params"])


def test_spec_unknown_artwork_404(client):
    r = client.get("/api/spec/nope")
    assert r.status_code == 404


def test_render_returns_svg_and_timing(client):
    payload = {
        "artwork": "geological",
        "seed": 42,
        "canvas": {"width": 200, "height": 200},
        "params": {"num_lines": 30, "x_resolution": 80},
    }
    r = client.post("/api/render", data=json.dumps(payload),
                    content_type="application/json")
    assert r.status_code == 200
    body = r.get_json()
    assert body["svg"].startswith("<svg")
    assert "ms" in body
    assert isinstance(body["ms"], (int, float))


def test_render_export_variant_has_white_bg(client):
    payload = {
        "artwork": "geological",
        "seed": 42,
        "canvas": {"width": 200, "height": 200},
        "params": {"num_lines": 20, "x_resolution": 60},
        "export": True,
    }
    r = client.post("/api/render", data=json.dumps(payload),
                    content_type="application/json")
    assert r.status_code == 200
    assert 'fill="white"' in r.get_json()["svg"]


def test_render_error_returns_json_400(client):
    payload = {"artwork": "does_not_exist", "seed": 1,
               "canvas": {"width": 10, "height": 10}, "params": {}}
    r = client.post("/api/render", data=json.dumps(payload),
                    content_type="application/json")
    assert r.status_code == 400
    assert "error" in r.get_json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'server.app'`

- [ ] **Step 3: Write `server/app.py`**

```python
"""Flask server: registry + spec + render endpoints, serving the static UI shell."""

import time
from pathlib import Path as FsPath

from flask import Flask, jsonify, request, send_from_directory

from engine.registry import Registry
from engine.types import Canvas
from engine.render import render_svg, render_print_optimized

STATIC_DIR = FsPath(__file__).parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    registry = Registry()

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory(STATIC_DIR, filename)

    @app.get("/api/artworks")
    def artworks():
        return jsonify([
            {"name": n,
             "title": registry.spec(n)["title"],
             "subtitle": registry.spec(n)["subtitle"]}
            for n in registry.names()
        ])

    @app.get("/api/spec/<name>")
    def spec(name):
        try:
            return jsonify(registry.spec(name))
        except KeyError:
            return jsonify({"error": f"unknown artwork: {name}"}), 404

    @app.post("/api/render")
    def render():
        data = request.get_json(force=True)
        name = data.get("artwork", "")
        seed = int(data.get("seed", 0))
        cdata = data.get("canvas", {})
        canvas = Canvas(width=float(cdata.get("width", 200)),
                        height=float(cdata.get("height", 200)))
        params = data.get("params", {})
        want_export = bool(data.get("export", False))
        try:
            t0 = time.perf_counter()
            merged = registry.merge_params(name, params)
            paths = registry.render_paths(name, params, seed=seed, canvas=canvas)
            if want_export:
                svg = render_print_optimized(canvas, paths, artwork=name,
                                             seed=seed, params=merged)
            else:
                svg = render_svg(canvas, paths)
            ms = (time.perf_counter() - t0) * 1000.0
        except KeyError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # surface algorithm errors to the UI
            return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400
        return jsonify({"svg": svg, "ms": round(ms, 1)})

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
```

- [ ] **Step 4: Create a placeholder `server/static/index.html`** so the index test passes before Task 7 builds the real UI

```html
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Procedural Prototyping</title></head>
<body><div id="app">loading…</div></body></html>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_server.py -v`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add server/app.py server/static/index.html tests/test_server.py
git commit -m "feat: Flask server with artworks/spec/render endpoints"
```

---

## Task 7: Generic data-driven UI shell

One HTML shell reused by every artwork: artwork switcher, canvas presets, auto-built grouped sliders from the spec, debounced live render, pan/zoom, seed/randomize/re-render, render timing, and draft/keeper SVG export. This task is verified manually (browser) plus the existing server smoke test for `/`.

**Files:**
- Modify: `server/static/index.html` (replace placeholder)
- Create: `server/static/style.css`
- Create: `server/static/app.js`

- [ ] **Step 1: Replace `server/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Procedural Prototyping</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <header>
    <span id="title">Procedural Prototyping</span>
    <span id="subtitle"></span>
    <select id="artwork-select" title="Artwork"></select>
  </header>

  <main>
    <aside id="panel"></aside>
    <section id="stage">
      <div id="canvas-wrap"><div id="canvas"></div></div>
      <div id="error" hidden></div>
    </section>
  </main>

  <footer>
    <label>seed <input id="seed" type="number" value="42" /></label>
    <button id="randomize">⚡ randomize</button>
    <button id="rerender">↻ re-render</button>
    <span id="timing">– ms</span>
    <button id="reset-zoom">⊙ reset zoom</button>
    <span id="zoom">100%</span>
    <span class="spacer"></span>
    <button id="save-draft">↓ save draft</button>
    <button id="save-keeper">★ save keeper</button>
  </footer>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `server/static/style.css`**

```css
:root {
  --bg: #0d0f12; --panel: #15181d; --panel2: #1b1f26;
  --fg: #c9d1d9; --muted: #6b7480; --accent: #4fd6c9; --line: #262b33;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 13px/1.4 "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
  height: 100vh; display: flex; flex-direction: column;
}
header {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid var(--line);
}
header #title { color: var(--accent); font-weight: 700; }
header #subtitle { color: var(--muted); }
header #artwork-select {
  margin-left: auto; background: var(--panel2); color: var(--fg);
  border: 1px solid var(--line); padding: 4px 8px; border-radius: 4px;
}
main { flex: 1; display: flex; min-height: 0; }
#panel {
  width: 280px; overflow-y: auto; padding: 8px;
  border-right: 1px solid var(--line); background: var(--panel);
}
.group { margin-bottom: 8px; border: 1px solid var(--line); border-radius: 4px; }
.group h3 {
  margin: 0; padding: 6px 10px; font-size: 11px; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted); background: var(--panel2);
}
.ctrl { padding: 6px 10px; }
.ctrl .row { display: flex; justify-content: space-between; }
.ctrl .val { color: var(--accent); }
.ctrl input[type=range] { width: 100%; accent-color: var(--accent); }
#stage { flex: 1; position: relative; display: flex;
  align-items: center; justify-content: center; overflow: hidden; }
#canvas-wrap { cursor: grab; }
#canvas svg { background: #fff; display: block; box-shadow: 0 0 0 1px var(--line); }
#error {
  position: absolute; top: 12px; left: 12px; right: 12px; padding: 10px;
  background: #3a1d1d; color: #ffb4b4; border: 1px solid #5a2a2a; border-radius: 4px;
  white-space: pre-wrap;
}
.preset-row { display: flex; gap: 4px; padding: 6px 10px; }
.preset-row button { flex: 1; }
button, .preset-row button {
  background: var(--panel2); color: var(--fg); border: 1px solid var(--line);
  padding: 5px 10px; border-radius: 4px; cursor: pointer;
}
button:hover { border-color: var(--accent); }
button.active { color: var(--accent); border-color: var(--accent); }
footer {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 16px; border-top: 1px solid var(--line); background: var(--panel);
}
footer .spacer { flex: 1; }
footer input#seed { width: 80px; background: var(--panel2); color: var(--fg);
  border: 1px solid var(--line); border-radius: 4px; padding: 3px 6px; }
#timing, #zoom { color: var(--muted); }
```

- [ ] **Step 3: Create `server/static/app.js`**

```javascript
const PRESETS = { A4: [210, 297], A3: [297, 420], Square: [200, 200] };
const state = {
  artwork: null, spec: null, params: {},
  canvas: { width: 200, height: 200 },
  seed: 42, view: { scale: 1, x: 0, y: 0 },
};
let renderTimer = null;

const $ = (sel) => document.querySelector(sel);

async function boot() {
  const artworks = await (await fetch("/api/artworks")).json();
  const select = $("#artwork-select");
  artworks.forEach((a) => {
    const opt = document.createElement("option");
    opt.value = a.name; opt.textContent = a.title;
    select.appendChild(opt);
  });
  select.style.display = artworks.length > 1 ? "" : "none";
  select.addEventListener("change", () => loadArtwork(select.value));

  wireFooter();
  await loadArtwork(artworks[0].name);
}

async function loadArtwork(name) {
  state.artwork = name;
  state.spec = await (await fetch(`/api/spec/${name}`)).json();
  $("#title").textContent = state.spec.title;
  $("#subtitle").textContent = state.spec.subtitle || "";
  state.params = {};
  state.spec.params.forEach((p) => (state.params[p.name] = p.default));
  buildPanel();
  scheduleRender();
}

function buildPanel() {
  const panel = $("#panel");
  panel.innerHTML = "";

  // Canvas group with presets + width/height
  const cg = group("Canvas");
  const presetRow = document.createElement("div");
  presetRow.className = "preset-row";
  Object.keys(PRESETS).forEach((name) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.addEventListener("click", () => {
      const [w, h] = PRESETS[name];
      state.canvas = { width: w, height: h };
      [...presetRow.children].forEach((c) => c.classList.remove("active"));
      b.classList.add("active");
      buildPanel(); scheduleRender();
    });
    if (state.canvas.width === PRESETS[name][0] &&
        state.canvas.height === PRESETS[name][1]) b.classList.add("active");
    presetRow.appendChild(b);
  });
  cg.appendChild(presetRow);
  cg.appendChild(rangeCtrl(
    { name: "width", label: "Width (mm)", min: 50, max: 420, step: 1,
      default: state.canvas.width },
    (v) => { state.canvas.width = v; scheduleRender(); }));
  cg.appendChild(rangeCtrl(
    { name: "height", label: "Height (mm)", min: 50, max: 420, step: 1,
      default: state.canvas.height },
    (v) => { state.canvas.height = v; scheduleRender(); }));
  panel.appendChild(cg);

  // Algorithm params grouped by spec group
  const groups = {};
  state.spec.params.forEach((p) => {
    (groups[p.group] = groups[p.group] || []).push(p);
  });
  Object.entries(groups).forEach(([gname, params]) => {
    const g = group(gname);
    params.forEach((p) => {
      g.appendChild(rangeCtrl(p, (v) => {
        state.params[p.name] = v; scheduleRender();
      }, state.params[p.name]));
    });
    panel.appendChild(g);
  });
}

function group(name) {
  const g = document.createElement("div");
  g.className = "group";
  const h = document.createElement("h3");
  h.textContent = name; g.appendChild(h);
  return g;
}

function rangeCtrl(p, onChange, current) {
  const wrap = document.createElement("div");
  wrap.className = "ctrl";
  const row = document.createElement("div");
  row.className = "row";
  const label = document.createElement("span");
  label.textContent = p.label;
  const val = document.createElement("span");
  val.className = "val";
  row.append(label, val);

  const input = document.createElement("input");
  input.type = "range";
  input.min = p.min; input.max = p.max; input.step = p.step;
  input.value = current !== undefined ? current : p.default;
  const fmt = () => (val.textContent = (+input.value).toString());
  fmt();
  input.addEventListener("input", () => { fmt(); onChange(+input.value); });

  wrap.append(row, input);
  return wrap;
}

function scheduleRender() {
  clearTimeout(renderTimer);
  renderTimer = setTimeout(doRender, 50);
}

async function doRender() {
  const payload = {
    artwork: state.artwork, seed: +$("#seed").value,
    canvas: state.canvas, params: state.params,
  };
  let body;
  try {
    const r = await fetch("/api/render", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    body = await r.json();
    if (!r.ok) throw new Error(body.error || "render failed");
  } catch (e) {
    showError(e.message); return;
  }
  hideError();
  $("#canvas").innerHTML = body.svg;
  $("#timing").textContent = `${body.ms} ms`;
  applyView();
}

function showError(msg) { const e = $("#error"); e.hidden = false; e.textContent = msg; }
function hideError() { $("#error").hidden = true; }

function applyView() {
  const wrap = $("#canvas-wrap");
  const v = state.view;
  wrap.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.scale})`;
  $("#zoom").textContent = `${Math.round(v.scale * 100)}%`;
}

function wireFooter() {
  $("#seed").addEventListener("change", scheduleRender);
  $("#randomize").addEventListener("click", () => {
    $("#seed").value = Math.floor(Math.random() * 1e9);
    scheduleRender();
  });
  $("#rerender").addEventListener("click", scheduleRender);
  $("#reset-zoom").addEventListener("click", () => {
    state.view = { scale: 1, x: 0, y: 0 }; applyView();
  });
  $("#save-draft").addEventListener("click", () => exportSvg("drafts"));
  $("#save-keeper").addEventListener("click", () => exportSvg("keepers"));

  // Pan + zoom
  const stage = $("#stage");
  let dragging = false, sx = 0, sy = 0;
  stage.addEventListener("mousedown", (e) => {
    dragging = true; sx = e.clientX - state.view.x; sy = e.clientY - state.view.y;
    $("#canvas-wrap").style.cursor = "grabbing";
  });
  window.addEventListener("mouseup", () => {
    dragging = false; $("#canvas-wrap").style.cursor = "grab";
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    state.view.x = e.clientX - sx; state.view.y = e.clientY - sy; applyView();
  });
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const f = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    state.view.scale = Math.max(0.1, Math.min(10, state.view.scale * f));
    applyView();
  }, { passive: false });
}

async function exportSvg(kind) {
  const payload = {
    artwork: state.artwork, seed: +$("#seed").value,
    canvas: state.canvas, params: state.params, export: true,
  };
  const r = await fetch("/api/render", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await r.json();
  if (!r.ok) { showError(body.error || "export failed"); return; }
  const blob = new Blob([body.svg], { type: "image/svg+xml" });
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = URL.createObjectURL(blob);
  a.download = `${state.artwork}_${kind}_s${$("#seed").value}_${stamp}.svg`;
  a.click();
  URL.revokeObjectURL(a.href);
}

boot();
```

- [ ] **Step 4: Manual verification**

Run: `python cli.py serve` (after Task 8) **or** `FLASK_APP=server.app python -m flask run`
Open `http://localhost:5000` and confirm:
- Artwork dropdown shows both artworks; switching rebuilds the sliders.
- Moving a slider updates the drawing within a fraction of a second; timing updates.
- Canvas presets A4/A3/Square change the canvas shape.
- Randomize changes the output; reset zoom recenters; scroll zooms; drag pans.
- "Save draft" / "Save keeper" download an SVG whose header comment contains the artwork, seed, and params.

- [ ] **Step 5: Run the server smoke test (still green)**

Run: `pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/static
git commit -m "feat: generic data-driven UI shell (sliders, live render, pan/zoom, export)"
```

---

## Task 8: CLI (`serve`, `list`, `batch`, `reproduce`)

A single entry point. `serve` runs the web app; `list` prints artworks; `batch` writes N random-seed SVGs to `output/`; `reproduce` reads an exported SVG's metadata header and regenerates it identically.

**Files:**
- Create: `cli.py`
- Test: `tests/test_reproduce.py`

- [ ] **Step 1: Write the failing test** — `tests/test_reproduce.py`

```python
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
    assert coerced["num_lines"] == 20            # int (step is 1)
    assert isinstance(coerced["num_lines"], int)
    assert abs(coerced["noise_scale"] - 0.012) < 1e-9   # float (fractional step)


def test_reproduce_is_deterministic():
    reg = Registry()
    canvas = Canvas(width=200, height=200)
    params = reg.merge_params("geological", {"num_lines": 15, "x_resolution": 50})
    a = reg.render_paths("geological", params, seed=99, canvas=canvas)
    b = reg.render_paths("geological", params, seed=99, canvas=canvas)
    assert [p.points for p in a] == [p.points for p in b]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reproduce.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cli'`

- [ ] **Step 3: Write `cli.py`**

```python
"""Command-line entry point: serve | list | batch | reproduce."""

import argparse
import random
import re
import sys
from pathlib import Path as FsPath

from engine.registry import Registry
from engine.types import Canvas
from engine.render import render_print_optimized

HEADER_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.DOTALL)


def parse_metadata_header(svg: str) -> dict:
    """Read the 'key: value | key: value' comment from an exported SVG."""
    m = HEADER_RE.search(svg)
    if not m:
        raise ValueError("no metadata header found in SVG")
    out = {}
    for part in m.group(1).split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def coerce_params(registry: Registry, artwork: str, raw: dict) -> dict:
    """Cast string param values using the artwork spec (int if step is integral)."""
    spec = {p["name"]: p for p in registry.spec(artwork)["params"]}
    out = {}
    for name, value in raw.items():
        if name not in spec:
            continue
        step = spec[name]["step"]
        out[name] = int(round(float(value))) if float(step).is_integer() else float(value)
    return out


def cmd_list(registry: Registry, _args) -> None:
    for name in registry.names():
        s = registry.spec(name)
        print(f"{name:18} {s['title']} — {s['subtitle']}")


def cmd_serve(_registry: Registry, args) -> None:
    from server.app import create_app
    create_app().run(debug=True, port=args.port)


def cmd_batch(registry: Registry, args) -> None:
    out_dir = FsPath("output/drafts")
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(width=args.width, height=args.height)
    for _ in range(args.count):
        seed = random.randint(0, 2**31 - 1)
        params = registry.defaults(args.artwork)
        paths = registry.render_paths(args.artwork, params, seed=seed, canvas=canvas)
        svg = render_print_optimized(canvas, paths, artwork=args.artwork,
                                     seed=seed, params=params)
        path = out_dir / f"{args.artwork}_s{seed}.svg"
        path.write_text(svg)
        print(f"wrote {path}")


def cmd_reproduce(registry: Registry, args) -> None:
    svg_in = FsPath(args.file).read_text()
    meta = parse_metadata_header(svg_in)
    artwork = meta.pop("artwork")
    seed = int(meta.pop("seed"))
    params = coerce_params(registry, artwork, meta)
    canvas = Canvas(width=args.width, height=args.height)
    paths = registry.render_paths(artwork, params, seed=seed, canvas=canvas)
    merged = registry.merge_params(artwork, params)
    svg_out = render_print_optimized(canvas, paths, artwork=artwork,
                                     seed=seed, params=merged)
    out = FsPath(args.out)
    out.write_text(svg_out)
    print(f"reproduced {artwork} (seed={seed}) -> {out}")


def main(argv=None) -> int:
    registry = Registry()
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=5000)
    p_serve.set_defaults(func=cmd_serve)

    sub.add_parser("list").set_defaults(func=cmd_list)

    p_batch = sub.add_parser("batch")
    p_batch.add_argument("artwork")
    p_batch.add_argument("--count", type=int, default=8)
    p_batch.add_argument("--width", type=float, default=200)
    p_batch.add_argument("--height", type=float, default=200)
    p_batch.set_defaults(func=cmd_batch)

    p_repro = sub.add_parser("reproduce")
    p_repro.add_argument("file")
    p_repro.add_argument("--out", default="output/keepers/reproduced.svg")
    p_repro.add_argument("--width", type=float, default=200)
    p_repro.add_argument("--height", type=float, default=200)
    p_repro.set_defaults(func=cmd_reproduce)

    args = parser.parse_args(argv)
    args.func(registry, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reproduce.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Verify the CLI end to end**

Run: `python cli.py list`
Expected: prints `geological` and `water_droplets` lines.

Run: `python cli.py batch geological --count 2`
Expected: writes two SVGs to `output/drafts/`.

- [ ] **Step 6: Commit**

```bash
git add cli.py tests/test_reproduce.py
git commit -m "feat: CLI with serve/list/batch/reproduce"
```

---

## Task 9: Full test sweep and README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Run the whole suite**

Run: `pytest -v`
Expected: all tests pass (types, render, registry, geological, water_droplets, server, reproduce).

- [ ] **Step 2: Write `README.md`**

```markdown
# Procedural Prototyping

A reproducible workbench for generative pen-plotter art (AxiDraw A3).

Each artwork is a pure function `geometry(canvas, params, rng) -> list[Path]`
plus a declarative parameter spec. The same code drives a live web UI and the
plotter-ready SVG export, so the preview is exactly what plots.

## Setup

    pip install -r requirements.txt

## Use

    python cli.py serve        # open http://localhost:5000 and explore
    python cli.py list         # list available artworks
    python cli.py batch geological --count 8        # write random SVGs to output/drafts
    python cli.py reproduce output/keepers/foo.svg  # regenerate from an SVG's metadata

## Add an artwork

Create `artworks/<name>/` with:
- `params.py` — `TITLE`, `SUBTITLE`, and `PARAMS` (a list of `Param`)
- `core.py`   — `def geometry(canvas, p, rng) -> list[Path]`

It auto-appears in the UI dropdown with sliders built from `PARAMS`.

## Test

    pytest
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage and artwork-authoring guide"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** pure `geometry` core (Tasks 4–5); `Param` spec + validation (Tasks 1, 3); renderer with print-optimized + metadata header (Task 2); registry auto-discovery + param merge (Task 3); Flask server endpoints (Task 6); generic data-driven UI with switcher, presets, pan/zoom, debounced render, draft/keeper export (Task 7); reproducibility header + `reproduce` (Tasks 2, 8); per-artwork determinism/bounds/spec tests (Tasks 3–5); both `geological` and `water_droplets` ported (Tasks 4–5).
- **Primitive set:** open polyline, closed polyline, and point (dot) all handled in `render.py` and represented by `Path` (Task 2).
- **Deferred (YAGNI, per spec):** `vpype` optimization pass; standalone-HTML "freeze" (Approach C).
- **Behavior note:** `geological` lacunarity/gain are now functional (original Python bug fixed); `water_droplets` circles are emitted as point-sampled closed polylines so the renderer needs only polylines.
```
