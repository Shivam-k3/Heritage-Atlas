"""Model inference. Two SEPARATE embedding spaces:

- CLIP (512-d): images, text-to-image queries, zero-shot feature tags, related sites.
- MiniLM (384-d): site description text search.

Never compare vectors across the two. Tag scores are raw cosine similarities, not probabilities.
Site type is never predicted: the uploader or site record owns that category.
Model imports stay lazy so unit tests and CI do not need torch.
"""

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from . import config
from .vocabulary import PromptConfig, prompt_config

CLIP_DIM = 512
TEXT_DIM = 384

CONFIG: PromptConfig = prompt_config()
FEATURES: tuple[str, ...] = CONFIG.labels
PROMPTS_VERSION: str = CONFIG.version
FEATURE_THRESHOLDS: dict[str, float | None] = CONFIG.thresholds
MAX_FEATURES = config.max_features()

_clip: Any = None
_text: Any = None
_feature_emb: np.ndarray | None = None
_negative_emb: np.ndarray | None = None

ImageSource = str | Path | BinaryIO


class InvalidImageError(ValueError):
    """The supplied bytes are not a decodable image."""


class ModelDimensionError(RuntimeError):
    """A loaded model does not match the vector column dimensions."""


def _load_image(source: ImageSource) -> Image.Image:
    try:
        opened = Image.open(source)
        image: Image.Image = ImageOps.exif_transpose(opened).convert("RGB")
        image.load()
        return image
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("file is not a valid JPEG, PNG or WebP image") from exc


def _check_dim(model: Any, expected: int, name: str) -> None:
    getter = (
        getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    )
    dimension = getter()
    if dimension != expected:
        raise ModelDimensionError(
            f"{name} returns {dimension}-d vectors, schema expects {expected}"
        )


def clip() -> Any:
    global _clip
    if _clip is None:
        from sentence_transformers import SentenceTransformer

        _clip = SentenceTransformer(config.clip_model_name(), device=config.model_device())
        _check_dim(_clip, CLIP_DIM, "CLIP")
    return _clip


def text_model() -> Any:
    global _text
    if _text is None:
        from sentence_transformers import SentenceTransformer

        _text = SentenceTransformer(config.text_embedding_model(), device=config.model_device())
        _check_dim(_text, TEXT_DIM, "text embedding model")
    return _text


def embed_image(source: ImageSource) -> np.ndarray:
    image = _load_image(source)
    vector = clip().encode([image], normalize_embeddings=True, batch_size=1)[0]
    return np.asarray(vector, dtype=np.float32)


def embed_images(sources: Iterable[ImageSource], batch_size: int = 8) -> np.ndarray:
    images = [_load_image(source) for source in sources]
    if not images:
        return np.empty((0, CLIP_DIM), dtype=np.float32)
    vectors = clip().encode(images, normalize_embeddings=True, batch_size=batch_size)
    return np.asarray(vectors, dtype=np.float32)


def embed_clip_text(query: str) -> np.ndarray:
    text = query.strip()
    if not text:
        raise ValueError("query must not be empty")
    vector = clip().encode(text, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32)


def embed_text(text: str) -> np.ndarray:
    value = text.strip()
    if not value:
        raise ValueError("text must not be empty")
    vector = text_model().encode(value, normalize_embeddings=True)
    return np.asarray(vector, dtype=np.float32)


def embed_texts(texts: Sequence[str], batch_size: int = 16) -> np.ndarray:
    values = [text.strip() for text in texts]
    if not values or any(not value for value in values):
        raise ValueError("texts must be non-empty")
    vectors = text_model().encode(values, normalize_embeddings=True, batch_size=batch_size)
    return np.asarray(vectors, dtype=np.float32)


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def _aggregate(prompt_sets: Sequence[Sequence[str]]) -> np.ndarray:
    """Mean of normalised prompt embeddings per feature, renormalised to unit length."""
    flat = [prompt for prompts in prompt_sets for prompt in prompts]
    encoded = np.asarray(clip().encode(flat, normalize_embeddings=True, batch_size=16))
    rows = []
    start = 0
    for prompts in prompt_sets:
        rows.append(_normalise(encoded[start : start + len(prompts)].mean(axis=0)))
        start += len(prompts)
    return np.asarray(rows, dtype=np.float32)


def _feature_embeddings() -> np.ndarray:
    global _feature_emb
    if _feature_emb is None:
        _feature_emb = _aggregate([feature.prompts for feature in CONFIG.features])
    return _feature_emb


def _negative_embeddings() -> np.ndarray | None:
    """Only usable when every feature defines at least one negative prompt."""
    global _negative_emb
    if _negative_emb is None:
        if not all(feature.negative_prompts for feature in CONFIG.features):
            return None
        _negative_emb = _aggregate([feature.negative_prompts for feature in CONFIG.features])
    return _negative_emb


def feature_scores(image_embedding: np.ndarray, use_negatives: bool = False) -> dict[str, float]:
    """Raw cosine similarity per feature. Negative prompts are opt-in and only for tuning."""
    vector = np.asarray(image_embedding, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("image embedding must not be zero")
    vector = vector / norm
    scores = _feature_embeddings() @ vector
    if use_negatives:
        negatives = _negative_embeddings()
        if negatives is not None:
            scores = scores - negatives @ vector
    return {label: float(scores[index]) for index, label in enumerate(FEATURES)}


def tag_image(
    image_embedding: np.ndarray,
    thresholds: dict[str, float | None] | None = None,
    use_negatives: bool = False,
) -> list[tuple[str, str, float]]:
    """Return (label, "feature", raw cosine) above each feature's acceptance threshold.

    An empty list is a valid outcome: no feature was confident enough. Site type is never
    emitted. Thresholds are cosine cut-offs, not probabilities.
    """
    limits = FEATURE_THRESHOLDS if thresholds is None else thresholds
    scored = feature_scores(image_embedding, use_negatives=use_negatives)
    accepted: list[tuple[str, str, float]] = []
    for label, score in scored.items():
        limit = limits.get(label)
        if limit is not None and score >= limit:
            accepted.append((label, "feature", score))
    accepted.sort(key=lambda item: item[2], reverse=True)
    return accepted[:MAX_FEATURES]


def model_info() -> dict[str, Any]:
    return {
        "clip_model": config.clip_model_name(),
        "clip_dimension": CLIP_DIM,
        "text_model": config.text_embedding_model(),
        "text_dimension": TEXT_DIM,
        "prompt_version": PROMPTS_VERSION,
        "features": list(FEATURES),
        "feature_thresholds": FEATURE_THRESHOLDS,
        "max_features": MAX_FEATURES,
    }
