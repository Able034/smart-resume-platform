from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import SystemLog
from tests.helpers import auth_headers, create_user, login_token


def test_register_duplicate_and_login_flow(client: TestClient, db_session):
    payload = {
        "account": "alice",
        "password": "Password123",
        "email": "alice@example.com",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["account"] == "alice"
    assert data["role"] == "USER"
    assert data["status"] == "ACTIVE"

    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40901

    login = client.post(
        "/api/v1/auth/login",
        json={"account": "alice", "password": "Password123"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["token"]

    failed_login = client.post(
        "/api/v1/auth/login",
        json={"account": "alice", "password": "wrong-password"},
    )
    assert failed_login.status_code == 401

    actions = db_session.scalars(
        select(SystemLog.action).order_by(SystemLog.log_id.asc())
    ).all()
    assert actions == ["REGISTER", "LOGIN"]


def test_me_requires_active_user(client: TestClient, db_session):
    user = create_user(db_session, "bob", "bob@example.com")
    token = login_token(client, "bob")

    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["data"]["account"] == "bob"

    user.status = "DISABLED"
    db_session.commit()

    disabled_me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert disabled_me.status_code == 401
