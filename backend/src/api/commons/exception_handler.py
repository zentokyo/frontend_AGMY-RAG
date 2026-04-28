from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.assistant.exceptions.assistant import AssistantException
from src.core.assistant.exceptions.exam import UserAlreadyTakingExamException
from src.core.commons.exception import BaseAppException


def register_exception_handler(app: FastAPI):
    @app.exception_handler(UserAlreadyTakingExamException)
    async def user_already_taking_exam_exception_handler(request: Request, exc: UserAlreadyTakingExamException):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": exc.message},
        )

    @app.exception_handler(AssistantException)
    async def assistant_exception_handler(request: Request, exc: AssistantException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": exc.message},
        )

    @app.exception_handler(BaseAppException)
    async def application_exception_handler(request: Request, exc: BaseAppException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": exc.message},
        )
