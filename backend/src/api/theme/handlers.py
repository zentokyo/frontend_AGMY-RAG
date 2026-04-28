import uuid
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Form, UploadFile, File
from fastapi.responses import Response

from src.api.theme.schema import ThemeResponseSchema, UserThemeResponseSchema
from src.core.assistant.dto.file import CreateFileDTO
from src.core.assistant.dto.theme import CreateThemeDTO
from src.core.assistant.use_cases.theme import CreateThemeUseCase, GetThemeListUseCase, GetThemeByIdUseCase, \
    GetThemeFileUseCase, GetUserThemeUseCase

theme_router = APIRouter(prefix="/themes", tags=["Themes"])


@theme_router.post("/")
@inject
async def create_theme_handler(
        title: Annotated[str, Form()],
        file_list: Annotated[list[UploadFile], File(...)],
        use_case: FromDishka[CreateThemeUseCase],
) -> ThemeResponseSchema:
    """Создать новую тему"""
    dto = CreateThemeDTO(
        title=title,
        file_list=[CreateFileDTO(filename=file.filename, file_data=file.file) for file in file_list]
    )

    theme = await use_case(dto)

    return ThemeResponseSchema.from_entity(theme)


@theme_router.get("/")
@inject
async def get_theme_list_handler(
        use_case: FromDishka[GetThemeListUseCase],
) -> list[ThemeResponseSchema]:
    """Получить список всех имеющихся тем"""
    theme_list = await use_case()

    return [ThemeResponseSchema.from_entity(theme) for theme in theme_list]


@theme_router.get("/{theme_id}/")
@inject
async def get_theme_by_id_handler(
        theme_id: uuid.UUID,
        use_case: FromDishka[GetThemeByIdUseCase],
) -> ThemeResponseSchema:
    """Получить тему по id"""
    theme = await use_case(theme_id)

    return ThemeResponseSchema.from_entity(theme)


@theme_router.get("/{theme_id}/file/")
@inject
async def get_theme_file_handler(
        theme_id: uuid.UUID,
        use_case: FromDishka[GetThemeFileUseCase],
) -> Response:
    zip_buffer = await use_case(theme_id)

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=docs.zip",
            "Content-Type": "application/zip"
        },

    )


@theme_router.get("/users/{user_id}/")
@inject
async def get_user_theme_list(
        user_id: int,
        use_case: FromDishka[GetUserThemeUseCase],
) -> list[UserThemeResponseSchema]:
    user_theme_list = await use_case(user_id)

    return [UserThemeResponseSchema.from_entity(user_theme) for user_theme in user_theme_list]
