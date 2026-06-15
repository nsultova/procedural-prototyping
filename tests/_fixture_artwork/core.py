from engine.types import Path, Canvas


def geometry(canvas: Canvas, p: dict, rng) -> list[Path]:
    paths = []
    for i in range(int(p["count"])):
        y = (i + 1) / (p["count"] + 1) * canvas.height
        paths.append(Path(points=[(0, y), (p["size"], y)]))
    return paths
