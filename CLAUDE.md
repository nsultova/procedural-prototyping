# CLAUDE.md

Reproducible workbench for **generative pen-plotter art** (AxiDraw A3). Pipeline: reverse-engineer an algorithm → pure geometry core + param spec → explore live in a web UI → export plotter-ready SVG. The pure core is the single source of truth — the same code feeds preview and export, so **what you see is what plots**.

**Output medium = pen on paper:** only black-and-white vector **paths** (no fill/color/raster); coordinates in **mm**; tone/density comes from how lines bunch, not gray values.

## Architectural invariant (do not violate)

**Adding or editing an artwork touches ONLY `artworks/<name>/` (`core.py` + `params.py`).** The registry auto-discovers any such package; the UI, export, and CLI pick it up for free. Never edit `engine/`, `server/`, `cli.py`, or the UI to support one artwork — wanting to change shared code for a single artwork means the artwork should express that thing itself.

Boundaries: `engine/` = pure types/render/registry (no HTTP); `server/app.py` = thin Flask + generic `static/` UI; `cli.py` = serve/list/batch/reproduce.

## Artwork contract

`core.py`: `def geometry(canvas: Canvas, p: dict, rng: random.Random) -> list[Path]` — see `engine/types.py` and `artworks/geological/` for the types and a worked example.

- **Pure & deterministic:** no I/O, no global state, no `random.seed`; all randomness via `rng` (derive sub-seeds with `rng.randint(...)`). Same seed + params ⇒ identical output.
- **Read params as `p["name"]`, never `p.get`** — the registry guarantees every `PARAMS` name is present, which is what makes `PARAMS` authoritative.
- **Coordinates:** mm, origin top-left; keep X within `[0, canvas.width]`; Y may intentionally bleed past top/bottom (e.g. geological) — assert such intent in a test.
- **`Path` is the only primitive** (3 forms in `engine/types.py`: open polyline, closed polyline, single-point dot). Emit circles as point-sampled closed polylines, never `<circle>`.

`params.py`: `TITLE`, `SUBTITLE`, `PARAMS` (list of `Param`), optional `PREVIEW` — see `artworks/geological/params.py`. The registry validates the spec.

## PARAMS vs. constants

- A value belongs in **`PARAMS`** iff it's a knob worth tuning live; `PARAMS` drives the sliders, defaults, reproducibility header, and the `p` dict. **Everything `geometry` reads must be in `PARAMS`.**
- Everything else is a **module constant in `core.py`** (e.g. water_droplets' `SECONDARY_*`). Prefer few meaningful sliders over exposing every coefficient.
- **`PREVIEW = {param: lighter_value}`** (optional): lighter values applied to interactive renders only — export is always full. Choose overrides that preserve *form*, not composition (geological: `x_resolution` 300→80).

## Dev workflow

- Use the venv: `.venv/bin/python`, `.venv/bin/pytest` (system Python lacks the deps). Run the app: `.venv/bin/python cli.py serve`.
- Keep `pytest` green; TDD where practical (artworks get determinism + in-bounds tests).
- Commits: branch off `master` first; **explicit `git add <paths>`, never `git add .`** (untracked `.venv/`); end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`; finish via `--no-ff` merge, then delete the branch.

## Don't regress (load-bearing — each fixed a real bug)

Server `threaded=True`; client single-flight rendering + adaptive preview→full scheduling; `localStorage` session persistence; reproducibility header `artwork|seed|canvas_*|params` kept in sync with `cli.parse_metadata_header` (powers `cli.py reproduce`).

## Reference

`docs/superpowers/specs/…-design.md` · `docs/superpowers/plans/…` · `README.md`
