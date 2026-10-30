from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.goals import router as goals_router
from app.api.calendar import router as calendar_router
from app.api.principles import router as principles_router
from app.api.preferences import router as preferences_router
from app.api.projects import router as projects_router
from app.api.profile import router as profile_router
from app.api.resume import router as resume_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Private API for the Personal AI Dashboard.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(system_router, prefix="/api/system")
app.include_router(profile_router, prefix="/api/profile")
app.include_router(goals_router, prefix="/api/goals")
app.include_router(principles_router, prefix="/api/principles")
app.include_router(preferences_router, prefix="/api/preferences")
app.include_router(projects_router, prefix="/api/projects")
app.include_router(tasks_router, prefix="/api/tasks")
app.include_router(resume_router, prefix="/api/resume")
app.include_router(calendar_router, prefix="/api/calendar")
app.include_router(ai_router, prefix="/api/ai")
