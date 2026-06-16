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
        out[name] = int(round(float(value))) if step.is_integer() else float(value)
    return out


def cmd_list(registry: Registry, _args) -> None:
    for name in registry.names():
        s = registry.spec(name)
        print(f"{name:18} {s['title']} — {s['subtitle']}")


def cmd_serve(registry: Registry, args) -> None:
    from server.app import create_app
    # threaded so a slow render never blocks static files or a newer request
    create_app(registry).run(debug=True, port=args.port, threaded=True)


def cmd_batch(registry: Registry, args) -> None:
    out_dir = FsPath("output/drafts")
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(width=args.width, height=args.height)
    params = registry.defaults(args.artwork)
    for _ in range(args.count):
        seed = random.randint(0, 2**31 - 1)
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
    # Canvas size is embedded in the recipe; fall back to flags for older files
    # that predate canvas metadata.
    width = float(meta.pop("canvas_width", args.width))
    height = float(meta.pop("canvas_height", args.height))
    params = coerce_params(registry, artwork, meta)
    canvas = Canvas(width=width, height=height)
    paths = registry.render_paths(artwork, params, seed=seed, canvas=canvas)
    merged = registry.merge_params(artwork, params)
    svg_out = render_print_optimized(canvas, paths, artwork=artwork,
                                     seed=seed, params=merged)
    out = FsPath(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
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
    # Only used as a fallback for SVGs exported before canvas size was embedded;
    # current files carry their own canvas dimensions in the metadata header.
    p_repro.add_argument("--width", type=float, default=200,
                         help="canvas width fallback (mm) if not in the SVG header")
    p_repro.add_argument("--height", type=float, default=200,
                         help="canvas height fallback (mm) if not in the SVG header")
    p_repro.set_defaults(func=cmd_reproduce)

    args = parser.parse_args(argv)
    args.func(registry, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
