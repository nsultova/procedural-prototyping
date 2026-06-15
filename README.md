# Procedural Prototyping

A reproducible workbench for generative pen-plotter art (AxiDraw A3).

Each artwork is a pure function `geometry(canvas, params, rng) -> list[Path]`
plus a declarative parameter spec. The **same code** drives a live web UI and
the plotter-ready SVG export, so the preview is exactly what plots — no more
keeping a Python algorithm and a hand-written HTML reimplementation in sync.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Use

```bash
.venv/bin/python cli.py serve        # open http://localhost:5000 and explore
.venv/bin/python cli.py list         # list available artworks
.venv/bin/python cli.py batch geological --count 8        # random SVGs -> output/drafts
.venv/bin/python cli.py reproduce output/keepers/foo.svg  # regenerate from an SVG's metadata
```

In the browser: pick an artwork from the dropdown, drag sliders to explore
(the canvas re-renders live), set/​randomize the seed, pan (drag) and zoom
(scroll). **Save draft** and **Save keeper** download a plotter-ready SVG whose
embedded comment records the artwork, seed, and every parameter — so any saved
file is a complete, re-runnable recipe.

## Add an artwork

Create `artworks/<name>/` with two files:

- `params.py` — `TITLE`, `SUBTITLE`, and `PARAMS` (a list of `Param`)
- `core.py`   — `def geometry(canvas, p, rng) -> list[Path]` (pure: params in,
  paths out; no SVG, no UI, no global state — read each knob via `p["name"]`)

It is auto-discovered: it appears in the UI dropdown with sliders built from
`PARAMS`, and export/batch/reproduce work for free. A `Path` is the single
primitive in three forms — open polyline, closed polyline (`closed=True`), or a
single-point dot — which together cover all pen-plotter output.

## Layout

```
engine/      types.py (Path/Canvas/Param), render.py (paths -> SVG), registry.py
artworks/    geological/, water_droplets/   (each: core.py + params.py)
server/      app.py (Flask) + static/ (the one generic UI shell)
cli.py       serve / list / batch / reproduce
output/      drafts/ + keepers/
tests/
```

## Test

```bash
.venv/bin/pytest
```
