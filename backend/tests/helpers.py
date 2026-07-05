from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Resume, UserAccount


def create_user(
    db: Session,
    account: str,
    email: str,
    password: str = "Password123",
    role: str = "USER",
    status: str = "ACTIVE",
) -> UserAccount:
    user = UserAccount(
        account=account,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_token(client: TestClient, account: str, password: str = "Password123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"account": account, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]["token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_resume(db: Session, user_id: int, title: str = "Test resume") -> Resume:
    resume = Resume(
        user_id=user_id,
        title=title,
        name="Test User",
        email="resume@example.com",
        skill_name="Python, FastAPI",
        personal_context="Backend development experience.",
        status="DRAFT",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume
