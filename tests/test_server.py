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


def test_render_malformed_body_returns_json_400(client):
    # Empty/garbage body must not crash with an HTML 500.
    r = client.post("/api/render", data="not json",
                    content_type="application/json")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_render_bad_seed_returns_json_400(client):
    payload = {"artwork": "geological", "seed": "abc",
               "canvas": {"width": 200, "height": 200}, "params": {}}
    r = client.post("/api/render", data=json.dumps(payload),
                    content_type="application/json")
    assert r.status_code == 400
    assert "error" in r.get_json()


def _render(client, **overrides):
    payload = {"artwork": "geological", "seed": 42,
               "canvas": {"width": 200, "height": 200},
               "params": {"num_lines": 20, "x_resolution": 300}}
    payload.update(overrides)
    r = client.post("/api/render", data=json.dumps(payload),
                    content_type="application/json")
    assert r.status_code == 200
    return r.get_json()["svg"]


def test_preview_render_is_lighter_than_full(client):
    # preview overlays geological's PREVIEW (x_resolution 300 -> 80), so the
    # preview SVG has far fewer sampled points and is shorter.
    full = _render(client)
    preview = _render(client, preview=True)
    assert len(preview) < len(full)


def test_export_ignores_preview_flag(client):
    # export must always render at full quality, even if preview is also set.
    plain_export = _render(client, export=True)
    export_with_preview = _render(client, export=True, preview=True)
    assert len(export_with_preview) == len(plain_export)
