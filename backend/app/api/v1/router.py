from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, jobs, opts, resumes, templates

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(templates.router, prefix="/resume-templates", tags=["templates"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(opts.router, tags=["opts"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
