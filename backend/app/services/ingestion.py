"""Folder scanning and draft GPS clustering for bulk ingestion.

Pure helpers only: no database, model or FastAPI imports, so they are unit-testable.
"""

from dataclasses import dataclass
from pathlib import Path

from .geo import haversine_km

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
DEFAULT_CLUSTER_RADIUS_M = 300
DRAFT_SITE_NAME = "Unnamed location cluster"
NO_GPS_SITE_NAME = "Unnamed location cluster (no GPS)"


@dataclass(frozen=True)
class ScanEntry:
    path: Path
    relative_path: str
    size: int


@dataclass(frozen=True)
class LocationCluster:
    image_ids: tuple[int, ...]
    lat: float
    lon: float


def scan_folder(root: Path) -> list[ScanEntry]:
    """Recursively list supported image files, sorted for a reproducible report."""
    if not root.is_dir():
        raise ValueError(f"not a folder: {root}")
    entries: list[ScanEntry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        entries.append(ScanEntry(path, path.relative_to(root).as_posix(), path.stat().st_size))
    return entries


def cluster_points(
    points: list[tuple[int, float, float]], radius_m: int = DEFAULT_CLUSTER_RADIUS_M
) -> list[LocationCluster]:
    """Single-linkage clusters of (image_id, lat, lon) using Haversine distance.

    Single linkage can chain two photos slightly further than the radius apart through a
    neighbour. That is acceptable for unverified draft clusters and keeps the code small.
    The centroid is the arithmetic mean, which is fine at a few hundred metres.
    """
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    parent = list(range(len(points)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    radius_km = radius_m / 1000
    for i, (_, lat_i, lon_i) in enumerate(points):
        for j in range(i + 1, len(points)):
            _, lat_j, lon_j = points[j]
            if haversine_km(lat_i, lon_i, lat_j, lon_j) <= radius_km:
                parent[find(j)] = find(i)

    grouped: dict[int, list[tuple[int, float, float]]] = {}
    for index, point in enumerate(points):
        grouped.setdefault(find(index), []).append(point)

    clusters = [
        LocationCluster(
            image_ids=tuple(sorted(image_id for image_id, _, _ in members)),
            lat=round(sum(lat for _, lat, _ in members) / len(members), 7),
            lon=round(sum(lon for _, _, lon in members) / len(members), 7),
        )
        for members in grouped.values()
    ]
    return sorted(clusters, key=lambda cluster: cluster.image_ids[0])
