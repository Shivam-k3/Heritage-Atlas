from datetime import date

from app.services.journal import generated_summary, top_features


def test_generated_summary_contains_stop_facts():
    text = generated_summary(
        2, "Adalaj Stepwell", "stepwell", "Gujarat", date(2026, 10, 31), 3, ["jali work"]
    )
    assert text.startswith("Stop 2: Adalaj Stepwell (stepwell, Gujarat).")
    assert "Visited 2026-10-31." in text
    assert "3 photographs on file." in text
    assert "Human-verified features: jali work." in text


def test_generated_summary_marks_missing_verification():
    text = generated_summary(1, "Rani ki Vav", None, None, None, 1, [])
    assert "1 photograph on file." in text
    assert "No human-verified feature tags yet." in text


def test_top_features_sorts_by_count_then_label():
    assert top_features({"b": 2, "a": 2, "c": 1}) == ["a", "b", "c"]
    assert top_features({"a": 1, "b": 2, "c": 3}, limit=2) == ["c", "b"]
