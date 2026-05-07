import os
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from src.api.answer.handlers import answer_router
from src.api.commons.exception_handler import register_exception_handler
from src.api.exam.handlers import exam_router
from src.api.exam_theme.handlers import exam_theme_router
from src.api.question.handlers import question_router
from src.api.stat.handlers import stat_router
from src.api.theme.handlers import theme_router
from src.ioc import container


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Assistant Backend",
        debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
        version="0.1.0",
    )

    register_exception_handler(app)

    app.include_router(theme_router)
    app.include_router(exam_theme_router)
    app.include_router(question_router)
    app.include_router(exam_router)
    app.include_router(answer_router)
    app.include_router(stat_router)

    setup_dishka(container, app)

    return app
