import os
from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.admin.auth import admin_auth_router, public_admin_auth_router
from src.api.admin.documents import admin_documents_router, public_admin_documents_router
from src.api.admin.questions import admin_questions_router, public_admin_questions_router
from src.api.app.answers import app_answers_router, public_app_answers_router
from src.api.app.auth import app_auth_router, public_app_auth_router
from src.api.app.course import app_course_router, public_app_course_router
from src.api.app.exams import app_exams_router, public_app_exams_router
from src.api.app.stats import app_stats_router, public_app_stats_router
from src.api.app.themes import app_themes_router, public_app_themes_router
from src.api.answer.handlers import answer_router
from src.api.commons.exception_handler import register_exception_handler
from src.api.exam.handlers import exam_router
from src.api.exam_theme.handlers import exam_theme_router
from src.api.question.handlers import question_router
from src.api.rag.handlers import rag_router
from src.api.stat.handlers import stat_router
from src.api.theme.handlers import theme_router
from src.ioc import container

ADMIN_STATIC_DIR = Path(
    os.getenv(
        "ADMIN_STATIC_DIR",
        Path(__file__).resolve().parent.parent / "static" / "admin",
    )
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Assistant Backend",
        debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
        version="0.1.0",
    )

    register_exception_handler(app)
    _setup_cors(app)

    app.include_router(public_admin_auth_router)
    app.include_router(public_admin_documents_router)
    app.include_router(public_admin_questions_router)
    app.include_router(public_app_auth_router)
    app.include_router(public_app_exams_router)
    app.include_router(public_app_answers_router)
    app.include_router(public_app_stats_router)
    app.include_router(public_app_themes_router)
    app.include_router(public_app_course_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_documents_router)
    app.include_router(admin_questions_router)
    app.include_router(app_stats_router)
    app.include_router(app_themes_router)
    app.include_router(app_answers_router)
    app.include_router(app_auth_router)
    app.include_router(app_exams_router)
    app.include_router(app_course_router)
    app.include_router(theme_router)
    app.include_router(exam_theme_router)
    app.include_router(question_router)
    app.include_router(exam_router)
    app.include_router(answer_router)
    app.include_router(rag_router)
    app.include_router(stat_router)

    _setup_admin_frontend(app)
    setup_dishka(container, app)

    return app


def _setup_cors(app: FastAPI) -> None:
    origins = [
        origin.strip()
        for origin in os.getenv("CLIENT_ORIGIN", "http://localhost:5174,http://127.0.0.1:5174").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _setup_admin_frontend(app: FastAPI) -> None:
    index_file = ADMIN_STATIC_DIR / "index.html"
    if not index_file.is_file():
        return

    assets_dir = ADMIN_STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="admin-assets")

    @app.get("/", include_in_schema=False)
    async def admin_index():
        return FileResponse(index_file)

    @app.get("/{path:path}", include_in_schema=False)
    async def admin_spa(path: str):
        if path.startswith(("api/", "internal/")):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        requested_file = (ADMIN_STATIC_DIR / path).resolve()
        if requested_file.is_relative_to(ADMIN_STATIC_DIR.resolve()) and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(index_file)
