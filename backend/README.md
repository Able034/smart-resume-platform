# Smart Resume Platform Backend

FastAPI + MySQL + LangChain backend scaffold for the smart resume platform.

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Before starting the API, edit `.env` and point `DATABASE_URL` to the MySQL instance in your VM. Run `../database/init.sql` inside the VM database first.
If Playwright or Chromium is not available, job crawling still falls back to static WebFetch and WebSearch snippets, but dynamic job pages may be less reliable.

## Main modules

- `app/api/v1/endpoints`: REST API endpoints.
- `app/services`: business logic and database operations.
- `app/agents`: LangChain-backed agent adapters. They run in mock mode by default.
- `app/models`: SQLAlchemy models matching the simplified 9-table design.
- `app/schemas`: Pydantic request/response and agent-output models.

## First useful test flow

1. `POST /api/v1/auth/register`
2. `POST /api/v1/auth/login`
3. `POST /api/v1/resumes/upload-pdf`
4. `GET /api/v1/resumes/{resumeId}`
5. `PUT /api/v1/resumes/{resumeId}`
6. `GET /api/v1/resume-templates`
7. `POST /api/v1/resumes/{resumeId}/generate-latex`
8. `POST /api/v1/resumes/{resumeId}/optimize`
