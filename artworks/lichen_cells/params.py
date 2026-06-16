from engine.types import Param

TITLE = "Lichen Cells"
SUBTITLE = "Voronoi cellular network with spine fringe · after liverwort cross-sections"

PARAMS = [
    Param("cell_count",     "Cell count",        50,   1500, 50,   600,  group="Cells"),
    Param("edge_bias",      "Edge density bias", 0.5,  5.0,  0.1,  2.0,  group="Cells"),
    Param("blob_roughness", "Blob roughness",    0.0,  0.5,  0.05, 0.2,  group="Blob shape"),
    Param("blob_lobes",     "Lobe count",        2,    12,   1,    6,    group="Blob shape"),
    Param("spine_count",    "Spine count",       20,   500,  10,   180,  group="Fringe"),
    Param("spine_length",   "Spine length (mm)", 2,    25,   1,    10,   group="Fringe"),
    Param("spine_width",    "Spine base (mm)",   0.2,  3.0,  0.1,  0.8,  group="Fringe"),
    Param("stroke_width",   "Stroke width",      0.1,  0.8,  0.05, 0.25, group="Style"),
]

PREVIEW = {"cell_count": 120, "spine_count": 60}
