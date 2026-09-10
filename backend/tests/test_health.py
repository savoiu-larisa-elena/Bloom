def test_root_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"].lower().startswith("bloom api")
