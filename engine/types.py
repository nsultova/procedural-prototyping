"""Core data types shared by the engine, artworks, and renderer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Canvas:
    """Drawing surface in millimetres."""
    width: float
    height: float
    margin: float = 2.0  # viewBox margin in mm


@dataclass
class Path:
    """The single output primitive for all artworks.

    Three forms, all plotter-native:
      - open polyline : len(points) >= 2, closed=False
      - closed polyline: closed=True
      - point / dot    : len(points) == 1
    """
    points: list                 # list[tuple[float, float]] in mm
    closed: bool = False
    width: float | None = None   # stroke width in mm; None -> renderer default


@dataclass
class Param:
    """Declarative slider specification for one algorithm knob."""
    name: str
    label: str
    min: float
    max: float
    step: float
    default: float
    group: str = "General"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "min": self.min,
            "max": self.max,
            "step": self.step,
            "default": self.default,
            "group": self.group,
        }
