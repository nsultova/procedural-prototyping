from engine.types import Param

TITLE = "Lichen Cells"
SUBTITLE = "branching skeleton · zone-differentiated Voronoi · spine fringe"

PARAMS = [
    # Skeleton
    Param("branch_count",     "Primary arms",       2,    8,    1,    4,    group="Skeleton"),
    Param("branch_spread",    "Tip spread (rad)",   0.2,  1.2,  0.05, 0.6,  group="Skeleton"),
    Param("branch_irregular", "Irregularity",       0.0,  1.0,  0.05, 0.4,  group="Skeleton"),
    # Cells
    Param("cell_count",       "Cell count",         50,   1500, 50,   600,  group="Cells"),
    Param("inner_zone",       "Inner zone ratio",   0.05, 0.55, 0.05, 0.25, group="Cells"),
    Param("void_count",       "Void count",         0,    20,   1,    8,    group="Cells"),
    # Fringe
    Param("spine_count",      "Spine count",        20,   500,  10,   180,  group="Fringe"),
    Param("spine_length",     "Spine length (mm)",  2,    25,   1,    10,   group="Fringe"),
    Param("spine_width",      "Spine base (mm)",    0.2,  3.0,  0.1,  0.8,  group="Fringe"),
    # Style
    Param("stroke_width",     "Stroke width",       0.1,  0.8,  0.05, 0.25, group="Style"),
]

PREVIEW = {"cell_count": 100, "spine_count": 50, "void_count": 4}
