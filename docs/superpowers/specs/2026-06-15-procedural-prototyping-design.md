# Procedural Prototyping — Design

**Date:** 2026-06-15
**Status:** Approved (ready for implementation planning)

## Purpose

A reproducible workbench for generative pen-plotter art. It replaces an ad-hoc
workflow (Jupyter notebooks, Processing, and a separate hand-written HTML file
per algorithm) with a single pipeline:

```
reference image / prompt
        │  (one-time, with Claude)
        ▼
  reverse-engineer the algorithm
        ▼
  artwork = pure geometry core + parameter spec   ← the durable single source of truth
        ├──→ live interactive UI (explore the parameter space)
        └──→ plotter-ready SVG export (AxiDraw A3)
```

The output medium is an AxiDraw A3 pen plotter, so all artwork output is
black-and-white vector paths.

## Problem being solved

Today each algorithm exists **twice**: once in Python (e.g.
`geological_strata.py`, the source of truth for SVG export) and once as a
complete hand-written JavaScript reimplementation inside an HTML file (e.g.
`geological-strata.html`, the file actually used for live tinkering and export).
The two must be kept in sync by hand, slider definitions are duplicated across
both, and the live preview is not guaranteed to match what actually plots. This
duplication is the core friction.

## Approach (chosen: "A — durable pure core + thin UI")

Write each algorithm **once** in Python as a pure geometry function. A single
generic local server renders any artwork; a single generic HTML shell builds its
controls from a declarative parameter spec. The live preview and the plotter
export run the *identical* code path, so what you see is what plots.

Rejected alternatives:

- **B — throwaway scratch + HTML tooling:** keeps the two-implementation problem
  we are trying to escape. Rejected.
- **C — durable core + snapshotable standalone HTML:** a clean superset of A that
  adds a "freeze to standalone HTML" step for sharing. Deferred (YAGNI) until
  shareable offline files are actually needed; A leaves the door open to it.

## Core abstraction

**An artwork is pure geometry, nothing else.** Each artwork is a folder with two
files and no knowledge of SVG, the server, or the UI.

```python
# artworks/<name>/core.py
def geometry(canvas: Canvas, p: dict, rng: Random) -> list[Path]:
    """Pure: params in → paths out. No SVG, no UI, no global state."""
    ...
    return paths
```

```python
# artworks/<name>/params.py
TITLE    = "Geological Strata"
SUBTITLE = "displaced line field · domain-warped noise terrain"
PARAMS = [
    Param("num_lines",     "Line count",    1, 400, 1,   200, group="Line field"),
    Param("displacement",  "Amplitude (mm)",5, 100, 1,   40,  group="Displacement"),
    Param("warp_strength", "Warp strength", 0, 8,   0.1, 2.5, group="Domain warping"),
    # ...
]
```

### Primitive set

`Path` is the single output primitive, in three forms — a complete basis for
pen-plotter art (the pen can only ever move along paths):

- **open polyline** — lines, flow-field trails, L-systems
- **closed polyline** — contours, rings, packed-circle/Voronoi cells
- **point** — stipple dabs / dots (a meaningful pen-up/pen-down primitive)

A `Path` carries `points: list[(x, y)]` in mm, plus optional `closed: bool` and
optional `width: float`.

### Why it scales to other techniques

The medium is the constraint: a plotter can only move a pen along a path, so
**every** technique's output is a set of paths. What varies between techniques
lives entirely *inside* `geometry()`, which is unconstrained Python (free to use
numpy, scipy, shapely, networkx, etc.). Examples mapping onto the same contract:
flow field → open paths; Voronoi/Delaunay → open paths; circle packing → closed
paths; stippling → points; reaction-diffusion → marching-squares closed paths;
L-system → open paths.

**Scalability test — adding technique #N touches only `artworks/<name>/`.** The
registry auto-discovers the folder, the UI auto-builds its sliders from `PARAMS`,
and export works for free. `engine/`, `server/`, and the UI are never touched.
This is also why the abstraction is the ideal reverse-engineering target: the
output of reverse-engineering an image is exactly those two small files.

### Known boundaries (do not break the architecture)

1. **Heavy algorithms** (reaction-diffusion, large particle sims) may exceed the
   ~130 ms render budget, making live tinkering laggier. Handled per-artwork
   later via a preview-resolution param or caching — not an architecture change.
2. **Non-slider interactions** (click-to-place a seed point, paint a mask) are
   out of scope for a sliders-only UI. The `Param` spec can grow new control
   types if ever needed. YAGNI today.

## Project layout

```
procedural-prototyping/
  engine/
    types.py      # Path, Canvas, Param dataclasses
    render.py     # list[Path] → SVG (wraps SvgBuilder)
    svg_utils.py  # ported from gen_art_dev (SvgBuilder, create_print_optimized)
    registry.py   # auto-discovers artworks/
  artworks/
    geological/   # core.py + params.py  ← the only thing written per piece
  server/
    app.py        # Flask: serves shell + spec + render endpoints
    static/       # index.html + app.js + style.css (one generic UI shell)
  cli.py          # serve / batch / list / reproduce commands
  output/
    drafts/       # timestamped exploration exports
    keepers/      # liked versions
  requirements.txt
```

Canvas size, presets (A4/A3/Square), width/height, and seed are **built-in**
(handled by engine + UI), so `PARAMS` lists only the algorithm's own knobs — no
per-artwork boilerplate for those. `rng` is passed into `geometry()` (a seeded
`random.Random` / numpy generator) so cores are reproducible and pure, with no
global `random.seed` mutation.

## Server & UI

### Server (`server/app.py`, Flask)

Artwork-agnostic. Endpoints:

| Endpoint | Responsibility |
|---|---|
| `GET /` | serve the static HTML shell |
| `GET /api/artworks` | registry lists discovered artworks (name, title, subtitle) |
| `GET /api/spec/<artwork>` | that artwork's `PARAMS` as JSON → drives sliders |
| `POST /api/render` | `{artwork, params, seed, canvas}` → `geometry()` → `render.py` → SVG |

`/api/render` catches exceptions from `geometry()` and returns the error as JSON
so a broken algorithm shows a message in the UI rather than crashing the session
— important while iterating on a new piece.

### UI shell (`static/`, written once, reused by every artwork)

Reproduces the existing aesthetic (dark grouped panels, teal accents, mono font)
but is fully data-driven:

- On load → fetch artwork list + spec → **auto-build grouped sliders** from
  `PARAMS`. No per-artwork HTML.
- Slider change → **debounced (~50 ms)** `POST /api/render` → inject returned SVG
  into the canvas.
- Built-in controls: canvas presets (A4/A3/Square), width/height, seed field,
  randomize, re-render, reset zoom, render timing (ms), pan/zoom, and the two
  export buttons (save draft / save keeper — see Export below).
- **Artwork switcher** (a `<select>` populated from `/api/artworks`): switches
  which algorithm is being explored without launching separate files. Hidden when
  only one artwork exists; adds essentially no complexity.

```
sliders ──debounced──> POST /api/render ──> geometry() ──> render.py ──> SVG ──> canvas
   ▲                                                                            │
   └──────────────────── auto-built from /api/spec ◄────────────────────────────┘
```

Launch: `python cli.py serve` opens the browser at the tool.

### Terminology

- **reference image** — one-time input to reverse-engineering; never part of the
  running tool.
- **artwork** — the algorithm (`core.py` + `params.py`); a reusable generator,
  not a single picture.
- **variation** — a concrete output produced by an artwork's sliders + seed;
  these are the new pieces, and exploring them is the point of the live UI.

## Export, reproducibility & testing

### Export (plotter-ready SVG)

"Save SVG" runs the same `render.py` path, then `create_print_optimized` (ported
from existing `svg_utils.py`): white background, `0.35px` strokes, mm-based
`viewBox` so it plots at true physical size. Preview and export share the
identical `geometry()` + renderer, so the preview *is* the plot.

- **A3 ready:** presets include A3 (297×420 mm); `viewBox` in real mm means
  AxiDraw / `axicli` reads correct dimensions with no scaling.
- **Drafts vs keepers:** *Save draft* → timestamped SVG in `output/drafts/`;
  *Save keeper* → `output/keepers/`. Both are plottable.
- **Optional later:** a `vpype` post-process pass (line merge/sort) to reduce pen
  travel. Noted, not built now (YAGNI).

### Reproducibility

Every exported SVG embeds a metadata comment recording **artwork name + seed +
every parameter value** (`create_print_optimized` already supports this):

```xml
<!-- artwork: geological | seed: 42 | num_lines: 200 | displacement: 40 | warp_strength: 2.5 | ... -->
```

`cli.py reproduce <file.svg>` reads that header back and re-renders identically.
Seed + params + pinned algorithm → deterministic output, guaranteed by the
passed-in `rng` (no global state).

### Testing

The pure `geometry()` contract keeps tests clean and per-artwork:

- **Determinism:** same seed + params → identical paths (catches nondeterminism).
- **In-bounds:** all points within canvas + margin (catches runaway coordinates).
- **Render:** `render.py` produces valid, parseable SVG with correct mm `viewBox`.
- **Registry/spec:** every artwork exposes a valid `PARAMS` spec (min ≤ default ≤
  max) so the UI cannot be fed a broken spec.

A newly reverse-engineered artwork is automatically covered by the
determinism / bounds / spec tests the moment its folder is added.

## Dependencies

- `svgwrite` (existing) — SVG construction
- `flask` — local server
- `numpy` (optional, available) — for algorithm internals that want it

## First implementation target

Port **two** existing pieces to the new structure as proving artworks, chosen to
exercise different primitives:

- `geological_strata.py` → `artworks/geological/` — open polylines (displaced
  scanlines).
- `water_droplets.py` → `artworks/water_droplets/` — closed polylines
  (concentric distorted rings).

Porting two different techniques in the first pass confirms not just that the
pipeline works once, but that the pure-core split, generic server/UI, slider
auto-generation, the artwork switcher, export parity, and the reproducibility
header all **generalize across techniques** — end to end.
