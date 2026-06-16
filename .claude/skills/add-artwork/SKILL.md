---
name: add-artwork
description: >
  Use this skill whenever the user wants to add a new artwork to this pen-plotter
  workbench — triggered by "add a new artwork", "create a new artwork called X",
  "let's make a [name] piece", "I want to build a new artwork", "add [algorithm]
  to the workbench", "new artwork: X". Also trigger when the user describes an
  algorithm they want to visualise and this project is the target. Invoke this
  before writing any code so the full artwork contract and workflow are in context.
---

# Adding a New Artwork

New artworks auto-register — create the package and the registry, UI, CLI, and
export all pick it up for free. You only need three files.

## Step 1 — Understand the algorithm first

Before touching any file, confirm:
- What algorithm / visual idea? Any reference (paper, code, description)?
- Which parameters are worth exposing as live sliders?
- Any intentional out-of-bounds geometry (e.g. lines bleeding past top/bottom)?

## Step 2 — Create the package

Use lowercase snake_case for `<name>` (e.g. `voronoi_cells`, `reaction_diffusion`).

```
artworks/<name>/__init__.py   ← empty
artworks/<name>/params.py
artworks/<name>/core.py
```

### params.py template

```python
from engine.types import Param

TITLE = "<Human-readable title>"
SUBTITLE = "<one-line description>"

PARAMS = [
    Param("param_name", "Label (unit)", min, max, step, default, group="Group"),
    # group related params: e.g. group="Growth", group="Style", group="Taper"
]

# PREVIEW = {"param_name": lighter_value}
# Optional — lighter values for interactive preview only (never affects export).
# Override params that make dragging snappier while preserving the artwork's form
# (e.g. reduce resolution/count, not a structural toggle).
```

**PARAMS rules:**
- Every value `geometry()` reads **must** be in PARAMS. No exceptions.
- Constants not worth exposing as sliders go as module-level values in core.py.
- `step` reflects meaningful resolution: `1` for integers, `0.05` for fine floats.

### core.py template

```python
"""<Algorithm name> — <one-line description of what it draws>."""

import math
from engine.types import Path, Canvas

# Internal tuning constants (not exposed as sliders)
# _SOME_RATIO = 0.35


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    W, H = canvas.width, canvas.height
    # Unpack all params at the top — always p["name"], never p.get()
    param = p["param_name"]
    ...

    paths: list[Path] = []
    # ... algorithm ...
    return paths
```

**Non-negotiable contract:**
- **Pure & deterministic**: no I/O, no `random.seed()`, no global state. All
  randomness via `rng`. Derive sub-seeds with `rng.randint(0, 2**31 - 1)`.
- Coordinates in mm, origin top-left. X stays within `[0, canvas.width]`. Y may
  intentionally bleed past top/bottom — but assert that intent in a test.
- `Path` is the only primitive (open polyline, closed polyline, or single dot).
  Never emit SVG `<circle>` — sample circles as closed polylines.
- Read every param as `p["name"]`, never `p.get()`.

**Engine types quick reference:**
```python
from engine.types import Canvas, Path, Param
Canvas(width, height, margin=2.0)            # dimensions in mm
Path(points=[(x,y), ...], closed=False, width=None)  # open polyline
Path(points=[(x,y), ...], closed=True,  width=0.3)   # closed polyline
Path(points=[(x,y)], width=None)                     # single dot
```

## Step 3 — Write tests

Create `tests/test_<name>.py`. Minimum:

```python
import random
from engine.types import Canvas
from artworks.<name> import core
from artworks.<name>.params import PARAMS


def _params(**overrides):
    p = {p.name: p.default for p in PARAMS}
    p.update(overrides)
    return p


def test_produces_paths():
    canvas = Canvas(width=200, height=200)
    assert len(core.geometry(canvas, _params(), random.Random(42))) > 0


def test_deterministic_for_same_seed():
    canvas = Canvas(width=200, height=200)
    a = core.geometry(canvas, _params(), random.Random(7))
    b = core.geometry(canvas, _params(), random.Random(7))
    assert [p.points for p in a] == [p.points for p in b]


def test_points_in_bounds():
    canvas = Canvas(width=200, height=200)
    for path in core.geometry(canvas, _params(), random.Random(42)):
        for x, y in path.points:
            assert -1e-6 <= x <= canvas.width + 1e-6
            assert -1e-6 <= y <= canvas.height + 1e-6
    # If Y bleeds intentionally, remove the Y assertion and add a comment here.


# Add feature tests: param=0 disables a layer, two seeds differ, etc.
```

**Keep tests fast:** override any resolution/count param in `_params()` so each
test completes in well under a second.

## Step 4 — Verify and commit

```bash
uv run pytest tests/test_<name>.py -v   # new tests pass
uv run pytest                           # full suite still green
```

Then commit following the project convention (branch → explicit add → `--no-ff`
merge → delete branch), with a `Co-Authored-By: <Model Name> <noreply@anthropic.com>`
trailer using the model name from your session (e.g. `Claude Sonnet 4.6`).
