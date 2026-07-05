from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import AwardInfo, EducationInfo, InternInfo, Opt, ProjectInfo, SystemLog
from tests.helpers import auth_headers, create_resume, create_user, login_token


def test_user_cannot_read_another_users_resume(client: TestClient, db_session):
    owner = create_user(db_session, "owner", "owner@example.com")
    viewer = create_user(db_session, "viewer", "viewer@example.com")
    resume = create_resume(db_session, owner.id)
    token = login_token(client, "viewer")

    response = client.get(
        f"/api/v1/resumes/{resume.resume_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Resume not found"


def test_delete_resume_soft_deletes_and_logs(client: TestClient, db_session):
    user = create_user(db_session, "delete_user", "delete_user@example.com")
    resume = create_resume(db_session, user.id, title="Delete me")
    token = login_token(client, "delete_user")

    response = client.delete(
        f"/api/v1/resumes/{resume.resume_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["data"] is True

    db_session.refresh(resume)
    assert resume.status == "ARCHIVED"
    assert resume.deleted_at is not None

    list_response = client.get("/api/v1/resumes", headers=auth_headers(token))
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert all(item["resumeId"] != resume.resume_id for item in items)

    detail_response = client.get(
        f"/api/v1/resumes/{resume.resume_id}",
        headers=auth_headers(token),
    )
    assert detail_response.status_code == 404
    assert db_session.scalar(
        select(SystemLog.action).where(SystemLog.action == "DELETE_RESUME")
    ) == "DELETE_RESUME"


def test_update_resume_replaces_detail_rows(client: TestClient, db_session):
    user = create_user(db_session, "resume_user", "resume_user@example.com")
    resume = create_resume(db_session, user.id)
    token = login_token(client, "resume_user")

    payload = {
        "title": "Updated resume",
        "name": "Resume User",
        "age": 22,
        "email": "resume_user@example.com",
        "phone": "13800000000",
        "expectedSalary": "15k-20k",
        "expectedPosition": "后端开发工程师",
        "skillName": "Python, FastAPI, MySQL",
        "personalContext": "负责过 Web API 和数据库设计。",
        "status": "SAVED",
        "educations": [
            {
                "university": "Test University",
                "major": "Software Engineering",
                "degree": "本科",
                "startTime": "2022-09-01",
                "endTime": "2026-06-30",
            }
        ],
        "projects": [
            {
                "projectName": "Smart Resume Platform",
                "role": "Backend",
                "introduction": "Resume management system",
                "content": "Designed REST APIs.",
                "startTime": "2025-01-01",
                "endTime": "2025-06-01",
            }
        ],
        "interns": [
            {
                "company": "Demo Company",
                "role": "Intern",
                "content": "Built internal tools.",
                "startTime": "2025-07-01",
                "endTime": "2025-09-01",
            }
        ],
        "awards": [
            {
                "name": "Programming Contest",
                "awardTime": "2024-05-01",
            }
        ],
    }

    response = client.put(
        f"/api/v1/resumes/{resume.resume_id}",
        json=payload,
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "SAVED"

    assert db_session.scalar(select(func.count()).select_from(EducationInfo)) == 1
    assert db_session.scalar(select(func.count()).select_from(ProjectInfo)) == 1
    assert db_session.scalar(select(func.count()).select_from(InternInfo)) == 1
    assert db_session.scalar(select(func.count()).select_from(AwardInfo)) == 1
    assert db_session.scalar(
        select(SystemLog.action).where(SystemLog.action == "UPDATE_RESUME")
    ) == "UPDATE_RESUME"


def test_generate_latex_fails_when_template_missing(client: TestClient, db_session):
    user = create_user(db_session, "latex_user", "latex_user@example.com")
    resume = create_resume(db_session, user.id)
    token = login_token(client, "latex_user")

    response = client.post(
        f"/api/v1/resumes/{resume.resume_id}/generate-latex",
        json={"resumeTemplateId": 99999},
        headers=auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Template not found"


def test_user_cannot_read_another_users_optimization(client: TestClient, db_session):
    owner = create_user(db_session, "opt_owner", "opt_owner@example.com")
    viewer = create_user(db_session, "opt_viewer", "opt_viewer@example.com")
    resume = create_resume(db_session, owner.id)
    opt = Opt(
        resume_id=resume.resume_id,
        content="Optimization content",
        result_json=None,
        score=80,
        status="NEW",
    )
    db_session.add(opt)
    db_session.commit()
    db_session.refresh(opt)
    token = login_token(client, "opt_viewer")

    response = client.get(
        f"/api/v1/opts/{opt.opt_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Resume not found"

    list_response = client.get(
        f"/api/v1/resumes/{resume.resume_id}/opts",
        headers=auth_headers(token),
    )
    assert list_response.status_code == 404
