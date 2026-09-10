from app.services.analysis_history import append_analysis
from tests.conftest import auth_header


def test_history_requires_auth(client):
    r = client.get("/api/history")
    assert r.status_code == 401


def test_history_empty_for_new_user(client, register_and_login):
    token = register_and_login("dana", "pw12345")["access_token"]
    r = client.get("/api/history", headers=auth_header(token))
    assert r.status_code == 200
    body = r.json()
    assert body["entries"] == []
    assert body["retention_days"] == 7


def test_history_dashboard_empty(client, register_and_login):
    token = register_and_login("dash_user", "pw12345")["access_token"]
    r = client.get("/api/history/dashboard", headers=auth_header(token))
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_count"] == 0
    assert body["retention_days"] == 7
    assert body["entries"] == []


def test_delete_history_requires_auth(client):
    r = client.delete("/api/history/1")
    assert r.status_code == 401


def test_delete_history_not_found(client, register_and_login):
    token = register_and_login("del_user", "pw12345")["access_token"]
    r = client.delete("/api/history/99999", headers=auth_header(token))
    assert r.status_code == 404


def test_history_stores_character_profiles(client, register_and_login):
    reg = register_and_login("char_user", "pw12345")
    headers = auth_header(reg["access_token"])
    payload = {
        "flesch_score": 70.0,
        "characters": {"candidates": [{"name": "Mira", "mentions": 3}]},
        "character_profile": {
            "enabled": True,
            "unavailable": False,
            "characters": [
                {
                    "name": "Mira",
                    "role_hint": "protagonist",
                    "goals_or_motivation": "Wants to find the hidden garden.",
                    "traits": ["curious", "brave"],
                }
            ],
            "arc_in_excerpt": [{"name": "Mira", "beat": "She decides to enter the gate."}],
        },
    }
    assert append_analysis("Mira opened the gate.", payload, user_id=reg["user_id"])
    listed = client.get("/api/history", headers=headers).json()["entries"][0]
    assert listed["characters"]["profiles"][0]["name"] == "Mira"
    assert listed["characters"]["profiles"][0]["arc_beat"] == "She decides to enter the gate."
    evolution = client.get("/api/history/characters/evolution", headers=headers).json()
    assert evolution["characters"][0]["name"] == "Mira"
    assert len(evolution["characters"][0]["snapshots"]) == 1


def test_delete_history_removes_entry(client, register_and_login):
    reg = register_and_login("del_ok", "pw12345")
    headers = auth_header(reg["access_token"])
    payload = {
        "flesch_score": 70.0,
        "flesch_kincaid_grade": 8.0,
        "emotion_tone": {"dominant_emotion": "joy"},
        "grammar": {"issue_count": 0},
        "style_consistency": {"consistency_score": 0.9},
    }
    assert append_analysis("Hello from delete test.", payload, user_id=reg["user_id"])
    listed = client.get("/api/history", headers=headers).json()["entries"]
    assert len(listed) == 1
    entry_id = listed[0]["id"]
    deleted = client.delete(f"/api/history/{entry_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert client.get("/api/history", headers=headers).json()["entries"] == []
