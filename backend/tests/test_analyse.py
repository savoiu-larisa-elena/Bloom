from tests.conftest import auth_header


def test_analyse_rejects_empty_text(client):
    r = client.post("/api/analyse", json={"text": "   "})
    assert r.status_code == 200
    body = r.json()
    assert body["error"]
    assert body["flesch_score"] is None


def test_analyse_happy_path_with_mocks(client, monkeypatch, register_and_login):
    import app.routers.analyse as analyse_router

    monkeypatch.setattr(analyse_router, "flesch_reading_ease_score", lambda text: 70.123)
    monkeypatch.setattr(analyse_router, "flesch_kincaid_grade_level", lambda text: 6.789)
    monkeypatch.setattr(analyse_router, "check_grammar", lambda text: {"issue_count": 2, "issues": []})
    monkeypatch.setattr(analyse_router, "neural_grammar_correct", lambda text: {"corrected": text})
    monkeypatch.setattr(analyse_router, "analyse_sentiment_polarity", lambda text: {"label": "neutral"})
    monkeypatch.setattr(
        analyse_router,
        "analyse_emotion_tone",
        lambda text: {"dominant_emotion": "joy", "scores": {"joy": 0.9}},
    )
    monkeypatch.setattr(analyse_router, "paraphrase_suggestions", lambda text: {"suggestions": []})
    monkeypatch.setattr(analyse_router, "analyse_linguistics", lambda text: {"word_count": 3})
    monkeypatch.setattr(
        analyse_router, "analyse_style_consistency", lambda text: {"consistency_score": 0.5}
    )
    monkeypatch.setattr(analyse_router, "analyse_characters", lambda text: {"characters": []})
    monkeypatch.setattr(analyse_router, "analyse_dialogue", lambda text: {"dialogue": []})
    monkeypatch.setattr(analyse_router, "analyse_coreference", lambda text: {"chains": []})
    monkeypatch.setattr(
        analyse_router,
        "analyse_character_profile_llm",
        lambda text, character_signals: {"profile": {}},
    )
    monkeypatch.setattr(analyse_router, "analyse_spacy", lambda text: {"ents": []})

    token = register_and_login("erin", "pw12345")["access_token"]
    r = client.post(
        "/api/analyse",
        json={"text": "Hello world."},
        headers=auth_header(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["flesch_score"] == 70.12
    assert body["flesch_kincaid_grade"] == 6.79
    assert body["emotion_tone"]["dominant_emotion"] == "joy"
