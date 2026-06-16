"""Discover, validate, and run artwork packages."""

import importlib
import pkgutil
import random
from pathlib import Path as FsPath

from engine.types import Canvas, Param


def validate_params(artwork: str, params: list[Param]) -> None:
    """Raise ValueError if any Param is malformed."""
    seen = set()
    for p in params:
        if p.name in seen:
            raise ValueError(f"{artwork}: duplicate param '{p.name}'")
        seen.add(p.name)
        if not (p.min <= p.default <= p.max):
            raise ValueError(
                f"{artwork}: param '{p.name}' default {p.default} "
                f"outside [{p.min}, {p.max}]"
            )
        if p.step <= 0:
            raise ValueError(f"{artwork}: param '{p.name}' step must be > 0")


class Registry:
    """Loads artwork packages of the form <package>.<name> with core+params."""

    def __init__(self, package: str = "artworks", folder: str = "artworks"):
        self._package = package
        self._folder = folder
        self._cache: dict = {}
        self._discover()

    def _discover(self) -> None:
        base = FsPath(self._folder)
        for mod in pkgutil.iter_modules([str(base)]):
            name = mod.name
            if name.startswith("__"):
                continue
            try:
                params_mod = importlib.import_module(f"{self._package}.{name}.params")
                core_mod = importlib.import_module(f"{self._package}.{name}.core")
            except ModuleNotFoundError:
                continue
            if not hasattr(params_mod, "PARAMS") or not hasattr(core_mod, "geometry"):
                continue
            validate_params(name, params_mod.PARAMS)
            self._cache[name] = (core_mod, params_mod)

    def names(self) -> list[str]:
        return sorted(self._cache.keys())

    def _get(self, name: str):
        if name not in self._cache:
            raise KeyError(f"unknown artwork: {name}")
        return self._cache[name]

    def spec(self, name: str) -> dict:
        _core, params_mod = self._get(name)
        return {
            "name": name,
            "title": getattr(params_mod, "TITLE", name),
            "subtitle": getattr(params_mod, "SUBTITLE", ""),
            "params": [p.to_dict() for p in params_mod.PARAMS],
        }

    def defaults(self, name: str) -> dict:
        _core, params_mod = self._get(name)
        return {p.name: p.default for p in params_mod.PARAMS}

    def merge_params(self, name: str, incoming: dict) -> dict:
        """Incoming values over spec defaults; unknown keys dropped."""
        merged = self.defaults(name)
        for key, value in incoming.items():
            if key in merged:
                merged[key] = value
        return merged

    def preview_params(self, name: str) -> dict:
        """Optional per-artwork param overrides for fast interactive previews.

        Returns the artwork's `PREVIEW` dict (empty if it declares none).
        """
        _core, params_mod = self._get(name)
        return dict(getattr(params_mod, "PREVIEW", {}))

    def render_paths(self, name: str, params: dict, seed: int, canvas: Canvas) -> list:
        core_mod, params_mod = self._get(name)
        merged = {p.name: p.default for p in params_mod.PARAMS}
        merged.update((k, v) for k, v in params.items() if k in merged)
        rng = random.Random(seed)
        return core_mod.geometry(canvas, merged, rng)
