import pytest


def test_register_returns_token(client):
    r = client.post("/api/auth/register", json={"username": "Alice_1", "password": "pw12345"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["username"] == "alice_1"
    assert isinstance(body["user_id"], int)


def test_register_rejects_invalid_username(client):
    r = client.post("/api/auth/register", json={"username": "ab", "password": "pw12345"})
    assert r.status_code == 400


def test_register_conflict(client):
    r1 = client.post("/api/auth/register", json={"username": "bob", "password": "pw12345"})
    assert r1.status_code == 200
    r2 = client.post("/api/auth/register", json={"username": "bob", "password": "pw12345"})
    assert r2.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={"username": "carl", "password": "pw12345"})
    r = client.post("/api/auth/login", json={"username": "carl", "password": "pw12345"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_failure(client):
    r = client.post("/api/auth/login", json={"username": "missing", "password": "pw12345"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_patch_me_password(client, register_and_login):
    token = register_and_login("patch_pw", "pw12345")["access_token"]
    r = client.patch(
        "/api/auth/me",
        headers={**auth_header(token), "Content-Type": "application/json"},
        json={"current_password": "pw12345", "new_password": "newpw12345"},
    )
    assert r.status_code == 200
    assert r.json()["username"] == "patch_pw"
    r2 = client.post(
        "/api/auth/login", json={"username": "patch_pw", "password": "newpw12345"}
    )
    assert r2.status_code == 200


def test_patch_me_wrong_current_password(client, register_and_login):
    token = register_and_login("patch_bad", "pw12345")["access_token"]
    r = client.patch(
        "/api/auth/me",
        headers={**auth_header(token), "Content-Type": "application/json"},
        json={"current_password": "wrong", "new_password": "newpw12345"},
    )
    assert r.status_code == 401
