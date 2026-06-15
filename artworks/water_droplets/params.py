from engine.types import Param

TITLE = "Water Droplets"
SUBTITLE = "generative plotter art · ripple interference"

PARAMS = [
    # Drops
    Param("num_drops",  "Number of drops", 1, 10, 1, 4,  group="Drops"),
    Param("max_rings",  "Max rings / drop", 2, 20, 1, 11, group="Drops"),
    # Ring geometry
    Param("ring_spacing",        "Inner spacing (mm)", 1.0, 10.0, 0.5,  4.0,  group="Ring geometry"),
    Param("ring_spacing_growth", "Spacing growth",     1.0, 1.5,  0.01, 1.11, group="Ring geometry"),
    # Distortion
    Param("distortion",        "Amplitude (mm)", 0.0, 5.0, 0.1,  1.4,  group="Distortion"),
    Param("freq1",             "Frequency 1",    1,   20,  1,    3,    group="Distortion"),
    Param("freq2",             "Frequency 2",    1,   20,  1,    7,    group="Distortion"),
    Param("freq3",             "Frequency 3",    1,   20,  1,    13,   group="Distortion"),
    Param("distortion_growth", "Growth / ring",  0.0, 0.3, 0.01, 0.05, group="Distortion"),
    # Wave interference
    Param("interference_strength",          "Strength (mm)", 0.0, 3.0, 0.05, 0.65, group="Wave interference"),
    Param("interference_wavelength_factor", "Wavelength ×",  0.5, 5.0, 0.1,  2.4,  group="Wave interference"),
    # Secondary drops
    Param("secondary_drops",        "Count",         0,   15,  1,   5,   group="Secondary drops"),
    Param("secondary_rings",        "Rings",         0,   8,   1,   3,   group="Secondary drops"),
    Param("secondary_ring_spacing", "Spacing (mm)",  0.2, 3.0, 0.1, 0.9, group="Secondary drops"),
    # Impact center
    Param("impact_rings",        "Impact rings",   0,   8,   1,    3,    group="Impact"),
    Param("impact_ring_spacing", "Impact spacing", 0.05, 1.0, 0.01, 0.22, group="Impact"),
    # Style
    Param("ring_points",  "Ring resolution", 32, 400, 8,    200,  group="Style"),
    Param("stroke_width", "Stroke width",    0.1, 1.0, 0.05, 0.35, group="Style"),
]
