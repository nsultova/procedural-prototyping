"""Flask server: registry + spec + render endpoints, serving the static UI shell."""

import time
from pathlib import Path as FsPath

from flask import Flask, jsonify, request, send_from_directory

from engine.registry import Registry
from engine.types import Canvas
from engine.render import render_svg, render_print_optimized

STATIC_DIR = FsPath(__file__).parent / "static"


def create_app(registry: Registry | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    registry = registry or Registry()

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory(STATIC_DIR, filename)

    @app.get("/api/artworks")
    def artworks():
        out = []
        for n in registry.names():
            s = registry.spec(n)
            out.append({"name": n, "title": s["title"], "subtitle": s["subtitle"]})
        return jsonify(out)

    @app.get("/api/spec/<name>")
    def spec(name):
        try:
            return jsonify(registry.spec(name))
        except KeyError:
            return jsonify({"error": f"unknown artwork: {name}"}), 404

    @app.post("/api/render")
    def render():
        # Parsing lives inside the try so malformed input (bad JSON, non-numeric
        # seed/canvas, unknown artwork) returns JSON 400, never an HTML 500.
        try:
            data = request.get_json(force=True, silent=True) or {}
            name = data.get("artwork", "")
            seed = int(data.get("seed", 0))
            cdata = data.get("canvas", {})
            canvas = Canvas(width=float(cdata.get("width", 200)),
                            height=float(cdata.get("height", 200)))
            params = data.get("params", {})
            want_export = data.get("export", False) is True  # only a real bool
            want_preview = data.get("preview", False) is True
            if want_preview and not want_export:
                # interactive preview: overlay the artwork's lighter PREVIEW values
                params = {**params, **registry.preview_params(name)}
            t0 = time.perf_counter()
            paths = registry.render_paths(name, params, seed=seed, canvas=canvas)
            if want_export:
                merged = registry.merge_params(name, params)
                svg = render_print_optimized(canvas, paths, artwork=name,
                                             seed=seed, params=merged)
            else:
                svg = render_svg(canvas, paths)
            ms = (time.perf_counter() - t0) * 1000.0
        except KeyError as exc:
            return jsonify({"error": exc.args[0] if exc.args else str(exc)}), 400
        except Exception as exc:  # surface algorithm/input errors to the UI
            return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 400
        return jsonify({"svg": svg, "ms": round(ms, 1)})

    return app


if __name__ == "__main__":
    # threaded so a slow render never blocks static files or a newer request
    create_app().run(debug=True, port=5000, threaded=True)
