from engine.types import Param

TITLE = "Fixture"
SUBTITLE = "test artwork"

PARAMS = [
    Param("count", "Count", 1, 10, 1, 3, group="Main"),
    Param("size", "Size (mm)", 1, 100, 1, 20, group="Main"),
]
