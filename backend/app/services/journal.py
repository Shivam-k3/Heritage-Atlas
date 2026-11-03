"""Template-based trail journal. Generated text never replaces the original field note."""

from collections.abc import Sequence
from datetime import date


def generated_summary(
    stop_order: int,
    site_name: str,
    category: str | None,
    region: str | None,
    visit_date: date | None,
    photos: int,
    verified_features: Sequence[str],
) -> str:
    place = ", ".join(part for part in (category, region) if part)
    heading = f"Stop {stop_order}: {site_name}" + (f" ({place})" if place else "")
    parts = [heading + "."]
    if visit_date:
        parts.append(f"Visited {visit_date}.")
    noun = "photograph" if photos == 1 else "photographs"
    parts.append(f"{photos} {noun} on file.")
    if verified_features:
        parts.append("Human-verified features: " + ", ".join(verified_features) + ".")
    else:
        parts.append("No human-verified feature tags yet.")
    return " ".join(parts)


def top_features(counts: dict[str, int], limit: int = 5) -> list[str]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [label for label, _ in ordered[:limit]]
