"""Feature prompt configuration for CLIP zero-shot tagging.

Prompts live in feature_prompts.json (version-controlled) so a run can be reproduced from
its prompt_version. Each feature is scored against the mean of its prompt embeddings; the
per-feature threshold is a raw cosine acceptance cut-off, not a probability.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from . import config


@dataclass(frozen=True)
class FeaturePrompt:
    label: str
    prompts: tuple[str, ...]
    negative_prompts: tuple[str, ...]
    threshold: float | None


@dataclass(frozen=True)
class PromptConfig:
    version: str
    features: tuple[FeaturePrompt, ...]

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(feature.label for feature in self.features)

    @property
    def thresholds(self) -> dict[str, float | None]:
        return {feature.label: feature.threshold for feature in self.features}


def _validate(data: dict) -> PromptConfig:
    version = str(data.get("version", "")).strip()
    if not version:
        raise ValueError("prompt config needs a non-empty version")
    features: list[FeaturePrompt] = []
    for item in data.get("features", []):
        label = str(item.get("label", "")).strip().lower()
        prompts = tuple(
            str(prompt).strip() for prompt in item.get("prompts", []) if str(prompt).strip()
        )
        negatives = tuple(
            str(prompt).strip()
            for prompt in item.get("negative_prompts", [])
            if str(prompt).strip()
        )
        threshold = item.get("threshold")
        if not label or not prompts:
            raise ValueError("every feature needs a label and at least one prompt")
        if len(prompts) > 4:
            raise ValueError(f"{label}: at most four prompt variants are supported")
        if threshold is not None and not -1 <= float(threshold) <= 1:
            raise ValueError(f"{label}: threshold must be a cosine in [-1, 1] or null")
        features.append(
            FeaturePrompt(
                label=label,
                prompts=prompts,
                negative_prompts=negatives,
                threshold=None if threshold is None else float(threshold),
            )
        )
    if not features:
        raise ValueError("prompt config needs at least one feature")
    if len({feature.label for feature in features}) != len(features):
        raise ValueError("feature labels must be unique")
    return PromptConfig(version=version, features=tuple(features))


def load_prompt_config(path: Path | None = None) -> PromptConfig:
    source = path or config.feature_prompts_path()
    return _validate(json.loads(Path(source).read_text(encoding="utf-8")))


_cached: PromptConfig | None = None


def prompt_config() -> PromptConfig:
    global _cached
    if _cached is None:
        _cached = load_prompt_config()
    return _cached


def clear_cache() -> None:
    global _cached
    _cached = None
