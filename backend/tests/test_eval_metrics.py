"""Metric and split helpers in the evaluation scripts."""

import importlib.util
from pathlib import Path

from app.services.evaluation import (
    choose_thresholds,
    evaluate,
    predict,
    site_split,
)

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tag_score_macro_and_micro():
    module = _load("eval_tagging")
    result = module.score(
        {1: {"temple"}, 2: set()},
        {1: {"temple", "domes"}, 2: {"domes"}},
        {"temple", "domes"},
    )
    assert result["macro_f1"] == 0.5
    assert result["micro_precision"] == round(1 / 3, 4)
    assert result["micro_recall"] == 1.0


def test_precision_at_5():
    module = _load("eval_search")
    assert module._precision([{"image_id": 1}, {"image_id": 9}], {1}) == 0.2
    assert module._precision([], {1}) == 0.0


def test_site_split_is_deterministic_and_site_wise():
    assert site_split(1) == site_split(1)
    assert site_split(1) in {"train", "tune", "test"}


def test_threshold_tuning_uses_only_the_supplied_rows():
    truth = {1: {"domes"}, 2: set(), 3: {"domes"}, 4: set()}
    scores = {1: {"domes": 0.40}, 2: {"domes": 0.10}, 3: {"domes": 0.35}, 4: {"domes": 0.30}}
    thresholds = choose_thresholds(truth, scores, ["domes"])
    assert thresholds["domes"] == 0.35
    predictions = {image_id: predict(row, thresholds) for image_id, row in scores.items()}
    assert predictions == {1: {"domes"}, 2: set(), 3: {"domes"}, 4: set()}


def test_label_without_tuning_positives_can_never_be_emitted():
    thresholds = choose_thresholds(
        {1: set(), 2: set()}, {1: {"domes": 0.9}, 2: {"domes": 0.8}}, ["domes"]
    )
    assert thresholds == {"domes": None}
    assert predict({"domes": 0.99}, thresholds) == set()


def test_evaluate_reports_false_positive_and_no_confident_frequency():
    truth = {1: {"domes"}, 2: set(), 3: {"jali work"}}
    predictions = {1: {"domes", "staircases"}, 2: set(), 3: set()}
    result = evaluate(truth, predictions, ["domes", "jali work", "staircases"])
    assert result["false_positive_frequency"] == round(1 / 3, 4)
    assert result["no_confident_feature_frequency"] == round(2 / 3, 4)
    assert result["per_label"]["domes"]["tp"] == 1
    assert result["per_label"]["staircases"]["fp"] == 1
    assert result["per_label"]["jali work"]["fn"] == 1
    assert result["predicted_label_counts"]["domes"] == 1
