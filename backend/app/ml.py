"""All model code lives here. Two SEPARATE embedding spaces:
   - CLIP (512-d): images + text-to-image queries
   - MiniLM (384-d): text-to-text over site descriptions
Never compare vectors across the two."""

import numpy as np
from PIL import Image

SITE_TYPES = ["stepwell", "fort", "temple", "palace", "haveli"]
FEATURES = [
    "carved pillars",
    "stone arches",
    "jali work",
    "domes",
    "staircases",
    "stone brackets",
    "water tank",
    "sculptural carvings",
    "decorative facade",
]
FEATURE_THRESHOLD = 0.22  # PLACEHOLDER: tune on your hand-labelled set
MAX_FEATURES = 4

_clip = _text = _label_emb = None


def clip():
    global _clip
    if _clip is None:
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        _clip = SentenceTransformer("clip-ViT-B-32")
    return _clip


def text_model():
    global _text
    if _text is None:
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        _text = SentenceTransformer("all-MiniLM-L6-v2")
    return _text


def embed_image(path_or_file) -> np.ndarray:
    img = Image.open(path_or_file).convert("RGB")
    return clip().encode(img, normalize_embeddings=True)


def embed_clip_text(q: str) -> np.ndarray:
    return clip().encode(q, normalize_embeddings=True)


def embed_text(q: str) -> np.ndarray:
    return text_model().encode(q, normalize_embeddings=True)


def _labels():
    global _label_emb
    if _label_emb is None:
        prompts = [f"a photo of a {t}, Indian heritage architecture" for t in SITE_TYPES] + [
            f"a photo showing {f}, Indian heritage architecture" for f in FEATURES
        ]
        _label_emb = clip().encode(prompts, normalize_embeddings=True)
    return _label_emb


def tag_image(img_emb: np.ndarray):
    """Returns [(label, type, raw_cosine)]. Scores are similarities, not probabilities."""
    sims = _labels() @ img_emb
    ns = len(SITE_TYPES)
    out = []
    best = int(np.argmax(sims[:ns]))
    out.append((SITE_TYPES[best], "site_type", float(sims[best])))
    feat = sims[ns:]
    for i in np.argsort(-feat)[:MAX_FEATURES]:
        if feat[i] >= FEATURE_THRESHOLD:
            out.append((FEATURES[i], "feature", float(feat[i])))
    return out
