import sys
from types import SimpleNamespace

import pytest
from app import ml


@pytest.fixture
def reset_models():
    original = (ml._text, ml._clip, {name: dict(state) for name, state in ml._readiness.items()})
    ml._text = None
    ml._clip = None
    for state in ml._readiness.values():
        state.update(
            loaded=False,
            initialization_seconds=None,
            error=None,
        )
    yield
    ml._text, ml._clip, saved_readiness = original
    for name, state in saved_readiness.items():
        ml._readiness[name].update(state)


def test_warm_up_loads_each_model_once_and_validates_dimensions(monkeypatch, reset_models):
    instances: list[str] = []

    class FakeModel:
        def __init__(self, name: str, device: str | None = None):
            instances.append(name)
            self.name = name

        def get_sentence_embedding_dimension(self) -> int:
            return ml.TEXT_DIM if "MiniLM" in self.name else ml.CLIP_DIM

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeModel),
    )

    ml.warm_up()
    ml.warm_up()

    assert instances == [ml.config.text_embedding_model(), ml.config.clip_model_name()]
    assert ml.model_readiness()["text"]["loaded"] is True
    assert ml.model_readiness()["clip"]["loaded"] is True
    assert ml.model_readiness()["text"]["dimension"] == 384
    assert ml.model_readiness()["clip"]["dimension"] == 512


def test_warm_up_reports_model_failure_without_affecting_other_model(monkeypatch, reset_models):
    class FailingModel:
        def __init__(self, name: str, device: str | None = None):
            if "MiniLM" in name:
                raise OSError("model files unavailable")

        def get_sentence_embedding_dimension(self) -> int:
            return ml.CLIP_DIM

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FailingModel),
    )

    ml.warm_up()

    readiness = ml.model_readiness()
    assert readiness["text"]["loaded"] is False
    assert "model files unavailable" in readiness["text"]["error"]
    assert readiness["clip"]["loaded"] is True


def test_database_health_does_not_require_models(monkeypatch):
    from app import db
    from app.main import health

    monkeypatch.setattr(db, "ping", lambda: True)
    monkeypatch.setattr(ml, "model_info", lambda: {"text_dimension": 384, "clip_dimension": 512})

    assert health() == {
        "status": "ok",
        "database": "ok",
        "models": {"text_dimension": 384, "clip_dimension": 512},
    }
