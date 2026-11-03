import numpy as np
import pytest
from app import ml, vocabulary


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _fake_features(monkeypatch) -> np.ndarray:
    """Orthonormal fake feature embeddings so similarity is exactly controllable."""
    labels = np.eye(len(ml.FEATURES), 512, dtype=np.float32)
    monkeypatch.setattr(ml, "_feature_emb", labels)
    return labels


def test_site_type_is_never_emitted(monkeypatch):
    labels = _fake_features(monkeypatch)
    thresholds = {label: 0.0 for label in ml.FEATURES}
    tags = ml.tag_image(_unit(labels[1]), thresholds=thresholds)
    assert tags
    assert {tag_type for _, tag_type, _ in tags} == {"feature"}
    assert tags[0][0] == ml.FEATURES[1]


def test_features_below_their_threshold_are_dropped(monkeypatch):
    labels = _fake_features(monkeypatch)
    thresholds = {label: 0.5 for label in ml.FEATURES}
    embedding = _unit(labels[0] + 0.1 * labels[1])
    tags = ml.tag_image(embedding, thresholds=thresholds)
    assert [tag[0] for tag in tags] == [ml.FEATURES[0]]


def test_no_confident_feature_is_a_valid_empty_result(monkeypatch):
    labels = _fake_features(monkeypatch)
    thresholds = {label: 0.9 for label in ml.FEATURES}
    embedding = _unit(labels.sum(axis=0))
    assert ml.tag_image(embedding, thresholds=thresholds) == []


def test_missing_threshold_means_no_forced_prediction(monkeypatch):
    labels = _fake_features(monkeypatch)
    assert ml.tag_image(_unit(labels[0]), thresholds={label: None for label in ml.FEATURES}) == []


def test_feature_count_is_capped(monkeypatch):
    labels = _fake_features(monkeypatch)
    monkeypatch.setattr(ml, "MAX_FEATURES", 2)
    thresholds = {label: 0.0 for label in ml.FEATURES}
    tags = ml.tag_image(_unit(labels.sum(axis=0)), thresholds=thresholds)
    assert len(tags) == 2


def test_scores_are_raw_cosine_not_probabilities(monkeypatch):
    labels = _fake_features(monkeypatch)
    scores = ml.feature_scores(_unit(labels[2]))
    assert abs(scores[ml.FEATURES[2]] - 1.0) < 1e-5
    assert abs(scores[ml.FEATURES[0]]) < 1e-5
    tags = ml.tag_image(_unit(labels[2]), thresholds={label: 0.0 for label in ml.FEATURES})
    assert abs(tags[0][2] - 1.0) < 1e-5


def test_negative_prompt_adjustment_is_applied(monkeypatch):
    labels = _fake_features(monkeypatch)
    monkeypatch.setattr(ml, "_negative_emb", 0.5 * labels)
    scores = ml.feature_scores(_unit(labels[0]), use_negatives=True)
    assert abs(scores[ml.FEATURES[0]] - 0.5) < 1e-5
    assert abs(scores[ml.FEATURES[1]]) < 1e-5


def test_prompt_config_is_versioned_and_validated():
    config = vocabulary.prompt_config()
    assert config.version == "heritage-v2"
    assert len(config.features) == 7
    assert all(3 <= len(feature.prompts) <= 4 for feature in config.features)
    assert all(
        feature.threshold is None or -1 <= feature.threshold <= 1 for feature in config.features
    )


def test_prompt_config_rejects_duplicate_labels_and_too_many_prompts():
    base = {
        "version": "v",
        "features": [
            {"label": "domes", "prompts": ["a"]},
            {"label": "domes", "prompts": ["b"]},
        ],
    }
    with pytest.raises(ValueError):
        vocabulary._validate(base)

    too_many = {
        "version": "v",
        "features": [{"label": "domes", "prompts": ["a", "b", "c", "d", "e"]}],
    }
    with pytest.raises(ValueError):
        vocabulary._validate(too_many)
