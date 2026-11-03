import sys
from types import ModuleType, SimpleNamespace

import pytest
from app import ai, config
from app.services import ai as ai_service


def test_ai_status_hides_key_and_reports_disabled(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = ai.status()

    assert result == {
        "enabled": False,
        "provider": "gemini",
        "model": config.gemini_model(),
        "configured": False,
        "available": False,
    }


def test_gemini_generation_uses_bounded_configuration(monkeypatch):
    calls: list[dict] = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append({"client": kwargs})
            self.models = self

        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=" grounded answer ")

    google_module = ModuleType("google")
    genai_module = ModuleType("google.genai")
    genai_module.types = SimpleNamespace(
        HttpOptions=lambda **kwargs: kwargs,
        GenerateContentConfig=lambda **kwargs: kwargs,
    )
    genai_module.Client = FakeClient
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setattr(ai.provider, "_timestamps", __import__("collections").deque())

    result = ai.generate("system", "prompt")

    assert result == "grounded answer"
    assert calls[0]["client"]["api_key"] == "secret"
    assert calls[1]["model"] == config.gemini_model()
    assert calls[1]["config"]["max_output_tokens"] == config.ai_max_output_tokens()


def test_missing_key_fails_without_importing_sdk(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ai.AIProviderError, match="not configured"):
        ai.generate("system", "prompt")


def test_chat_falls_back_to_retrieved_site_when_gemini_unavailable(monkeypatch):
    site = {
        "id": 1,
        "name": "Rani ki Vav",
        "region": "Gujarat",
        "category": "stepwell",
        "description": "Original field note",
        "images": [],
    }
    monkeypatch.setattr(ai_service.sites_repo, "get_site", lambda conn, site_id: site)
    monkeypatch.setattr(
        ai_service.ai,
        "generate",
        lambda *_: (_ for _ in ()).throw(ai.AIProviderError("quota exhausted")),
    )

    result = ai_service.chat(object(), "Explain this site", [], 1, None)

    assert result["ai_generated"] is False
    assert result["sites"][0]["name"] == "Rani ki Vav"
    assert "quota exhausted" in result["warnings"]


def test_trail_suggestion_rejects_unknown_ids_and_preserves_coordinates(monkeypatch):
    records = {
        1: {
            "id": 1,
            "name": "A",
            "region": "Gujarat",
            "category": "stepwell",
            "lat": 23,
            "lon": 72,
        },
        2: {
            "id": 2,
            "name": "B",
            "region": "Rajasthan",
            "category": "fort",
            "lat": None,
            "lon": None,
        },
    }
    monkeypatch.setattr(
        ai_service.sites_repo, "get_site", lambda conn, site_id: records.get(site_id)
    )
    monkeypatch.setattr(
        ai_service.ai, "generate", lambda *_: (_ for _ in ()).throw(ai.AIProviderError("disabled"))
    )

    result = ai_service.suggest_trail(object(), [1, 2], None, None)

    assert result["distance_mode"] == "straight_line"
    assert result["missing_coordinates"] == [2]
    assert result["sites"][0]["lat"] == 23
