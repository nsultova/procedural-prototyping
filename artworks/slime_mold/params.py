from engine.types import Param

TITLE = "Slime Mould"
SUBTITLE = "space-colonization vein network"

PARAMS = [
    # Growth
    Param("num_attractors",  "Food points",      100,  3000, 50,  1800, group="Growth"),
    Param("influence_radius","Influence (mm)",   5,    80,   1,    35,  group="Growth"),
    Param("kill_radius",     "Kill radius (mm)",  1,    20,   0.5,  3,   group="Growth"),
    Param("step_size",       "Step (mm)",         0.5,  8,    0.5,  2.0, group="Growth"),
    Param("max_steps",       "Max steps",         50,   1200, 10,   700, group="Growth"),
    # Form
    Param("frontier_bias",   "Frontier bias",     0.0,  4.0,  0.25, 1.5, group="Form"),
    Param("wander",          "Wander",            0.0,  1.0,  0.05, 0.3, group="Form"),
    # Taper
    Param("min_width",       "Min width (mm)",    0.1,  1.0,  0.05, 0.25, group="Taper"),
    Param("max_width",       "Max width (mm)",    0.3,  4.0,  0.1,  1.6,  group="Taper"),
    Param("width_exponent",  "Taper exponent",    0.3,  3.0,  0.1,  0.7,  group="Taper"),
    # Mesh — thin reconnecting links -> loops/cells (density 0 -> off)
    Param("mesh_density",    "Mesh density",      0.0,  1.0,  0.05, 0.45, group="Mesh"),
    Param("mesh_dist",       "Mesh reach (mm)",   2,    30,   1,    9,    group="Mesh"),
    # Bursts — radial marks at branch-junction nodes
    Param("burst_density",   "Junction density",  0.0,  1.0,  0.05, 0.8,  group="Bursts"),
    Param("burst_strokes",   "Strokes/junction",  1,    20,   1,    7,    group="Bursts"),
    Param("burst_reach",     "Burst reach (mm)",  0.5,  8.0,  0.5,  2.5,  group="Bursts"),
    Param("burst_length",    "Stroke length (mm)",0.5,  6.0,  0.5,  2.0,  group="Bursts"),
]

# Interactive previews: fewer food points / steps for snappy dragging.
PREVIEW = {"num_attractors": 400, "max_steps": 350}
