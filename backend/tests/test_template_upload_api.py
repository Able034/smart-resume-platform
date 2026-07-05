from fastapi.testclient import TestClient

from tests.helpers import auth_headers, create_user, login_token


def test_admin_template_upload_rejects_unsupported_file(client: TestClient, db_session):
    create_user(db_session, "template_admin", "template_admin@example.com", role="ADMIN")
    token = login_token(client, "template_admin")

    response = client.post(
        "/api/v1/admin/resume-templates/upload",
        data={"templateName": "Bad Template"},
        files={"file": ("template.txt", b"not latex", "text/plain")},
        headers=auth_headers(token),
    )
    assert response.status_code == 400
    assert "Only .tex and .zip" in response.json()["message"]
