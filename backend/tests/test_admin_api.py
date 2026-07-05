from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import SystemLog, UserAccount
from tests.helpers import auth_headers, create_user, login_token


def test_non_admin_cannot_open_admin_users(client: TestClient, db_session):
    create_user(db_session, "normal", "normal@example.com")
    token = login_token(client, "normal")

    response = client.get("/api/v1/admin/users", headers=auth_headers(token))
    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_admin_can_disable_enable_user_and_read_logs(client: TestClient, db_session):
    admin = create_user(
        db_session,
        "admin",
        "admin@example.com",
        role="ADMIN",
    )
    target = create_user(db_session, "target", "target@example.com")
    token = login_token(client, "admin")

    disabled = client.patch(
        f"/api/v1/admin/users/{target.id}/disable",
        headers=auth_headers(token),
    )
    assert disabled.status_code == 200
    assert disabled.json()["data"]["status"] == "DISABLED"
    db_session.refresh(target)
    assert target.status == "DISABLED"

    enabled = client.patch(
        f"/api/v1/admin/users/{target.id}/enable",
        headers=auth_headers(token),
    )
    assert enabled.status_code == 200
    assert enabled.json()["data"]["status"] == "ACTIVE"

    logs = client.get(
        "/api/v1/admin/logs?action=DISABLE_USER",
        headers=auth_headers(token),
    )
    assert logs.status_code == 200
    payload = logs.json()["data"]
    assert payload["total"] == 1
    assert payload["items"][0]["userId"] == admin.id
    assert payload["items"][0]["targetId"] == str(target.id)

    persisted_actions = db_session.scalars(
        select(SystemLog.action).order_by(SystemLog.log_id.asc())
    ).all()
    assert persisted_actions == ["LOGIN", "DISABLE_USER", "ENABLE_USER"]


def test_admin_user_search_and_status_filter(client: TestClient, db_session):
    create_user(db_session, "admin2", "admin2@example.com", role="ADMIN")
    create_user(db_session, "active_user", "active@example.com")
    disabled_user = create_user(db_session, "disabled_user", "disabled@example.com")
    disabled_user.status = "DISABLED"
    db_session.commit()
    token = login_token(client, "admin2")

    response = client.get(
        "/api/v1/admin/users?keyword=disabled&status=DISABLED",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["account"] == "disabled_user"

    assert db_session.scalar(select(UserAccount).where(UserAccount.account == "active_user"))
