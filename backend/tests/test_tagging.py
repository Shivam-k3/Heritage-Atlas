import numpy as np
from app import ml


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _fake_labels(monkeypatch) -> np.ndarray:
    """Orthonormal fake label embeddings so similarity is exactly controllable."""
    n = len(ml.SITE_TYPES) + len(ml.FEATURES)
    labels = np.eye(n, 512, dtype=np.float32)
    monkeypatch.setattr(ml, "_label_emb", labels)
    return labels


def test_exactly_one_site_type(monkeypatch):
    labels = _fake_labels(monkeypatch)
    tags = ml.tag_image(_unit(labels[1] + 0.1 * labels[0]))
    site_types = [t for t in tags if t[1] == "site_type"]
    assert len(site_types) == 1
    assert site_types[0][0] == ml.SITE_TYPES[1]


def test_features_below_threshold_are_dropped(monkeypatch):
    labels = _fake_labels(monkeypatch)
    ns = len(ml.SITE_TYPES)
    emb = _unit(labels[0] + 0.05 * labels[ns])  # feature 0 similarity far below threshold
    tags = ml.tag_image(emb)
    assert all(t[1] != "feature" for t in tags)


def test_feature_count_is_capped(monkeypatch):
    labels = _fake_labels(monkeypatch)
    ns = len(ml.SITE_TYPES)
    emb = _unit(labels[0] + labels[ns : ns + len(ml.FEATURES)].sum(axis=0))
    monkeypatch.setattr(ml, "FEATURE_THRESHOLD", 0.0)
    features = [t for t in ml.tag_image(emb) if t[1] == "feature"]
    assert len(features) == ml.MAX_FEATURES


def test_scores_are_raw_cosine_not_probabilities(monkeypatch):
    labels = _fake_labels(monkeypatch)
    tags = ml.tag_image(_unit(labels[2]))
    assert abs(tags[0][2] - 1.0) < 1e-5
