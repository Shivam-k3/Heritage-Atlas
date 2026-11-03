from app.services.licences import clean_text, is_reusable, normalise_licence


def test_clean_text_strips_html_and_collapses_space():
    assert clean_text("  <b>CC BY-SA 4.0</b>\n ") == "CC BY-SA 4.0"


def test_normalise_common_licences():
    assert normalise_licence("cc-by-sa-4.0") == "CC BY-SA 4.0"
    assert normalise_licence("CC BY 4.0") == "CC BY 4.0"
    assert normalise_licence("CC0 1.0") == "CC0"
    assert normalise_licence("Public domain") == "Public domain"


def test_reuse_rejects_missing_or_non_free_licences():
    assert is_reusable("CC BY-SA 4.0")
    assert is_reusable("CC0")
    assert not is_reusable("")
    assert not is_reusable("All rights reserved")
    assert not is_reusable("Non-free")
