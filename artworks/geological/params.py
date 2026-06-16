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

# Parameter overrides applied only to interactive (preview) renders, never to
# export. Reducing x_resolution keeps line count/density and overall form intact
# while cutting per-line sampling ~4x for snappy live feedback; the full-quality
# render fires once the user stops adjusting.
PREVIEW = {"x_resolution": 80}
