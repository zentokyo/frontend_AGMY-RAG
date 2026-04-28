import uuid
import zipfile
from io import BytesIO

from unidecode import unidecode

from src.core.assistant.dto.theme import CreateThemeDTO
from src.core.assistant.entities.exam import ExamTheme
from src.core.assistant.entities.file import File
from src.core.assistant.entities.theme import Theme, UserTheme, ThemeFile
from src.core.assistant.exceptions.theme import ThemeTitleNotUniqueException
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository
from src.core.assistant.interfaces.uow.theme import ThemeUnitOfWork
from src.core.commons.interfaces.storages.s3 import S3Storage


class BaseThemeUseCase:
    def __init__(self, theme_repository: ThemeRepository):
        self._theme_repository = theme_repository


class CreateThemeUseCase:
    def __init__(
            self,
            uow: ThemeUnitOfWork,
            s3_storage: S3Storage,
    ):
        self._uow = uow
        self._s3_storage = s3_storage

    async def __call__(self, create_theme_dto: CreateThemeDTO) -> Theme:
        async with self._uow:
            if not await self._uow.theme_repository.title_is_unique(create_theme_dto.title):
                raise ThemeTitleNotUniqueException(title=create_theme_dto.title)

            current_order = await self._uow.theme_repository.get_max_order()
            further_order = current_order + 1

            theme = Theme(
                title=create_theme_dto.title,
                theme_order=further_order,
            )
            exam_theme = ExamTheme(
                title=create_theme_dto.title,
                exam_theme_order=further_order,
            )

            await self._uow.theme_repository.add_theme(theme)
            await self._uow.exam_theme_repository.add_exam_theme(exam_theme)

            for file in create_theme_dto.file_list:
                file_entity = File(filename=unidecode(file.filename))
                await self._uow.file_repository.add_file(file_entity)
                theme_file = ThemeFile(
                    theme_id=theme.theme_id,
                    file_id=file_entity.file_id,
                )
                await self._uow.theme_file_repository.add_theme_file(theme_file)
                await self._s3_storage.upload_file(file.file_data.read(), file_entity.filename)
                theme.file_list.append(file_entity)

            await self._uow.commit()

            return theme


class GetThemeByIdUseCase(BaseThemeUseCase):
    async def __call__(self, theme_id: uuid.UUID) -> Theme:
        return await self._theme_repository.get_theme_by_id(theme_id)


class GetThemeListUseCase(BaseThemeUseCase):
    async def __call__(self) -> list[Theme]:
        return await self._theme_repository.get_theme_list()


class GetThemeFileUseCase(BaseThemeUseCase):
    def __init__(
            self,
            theme_repository: ThemeRepository,
            s3_storage: S3Storage,
    ):
        super().__init__(theme_repository)
        self._s3_storage = s3_storage

    async def __call__(self, theme_id: uuid.UUID) -> BytesIO:
        theme = await self._theme_repository.get_theme_by_id(theme_id)

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for file in theme.file_list:
                pdf_file = await self._s3_storage.download_file(file.filename)
                zip_file.writestr(file.filename, pdf_file)

        zip_buffer.seek(0)

        return zip_buffer


class GetUserThemeUseCase(BaseThemeUseCase):  # Костыльные костыли
    def __init__(
            self,
            theme_repository: ThemeRepository,
            exam_repository: ExamRepository,
    ):
        super().__init__(theme_repository)
        self._exam_repository = exam_repository

    async def __call__(self, user_id: int) -> list[UserTheme]:
        theme_list = await self._theme_repository.get_theme_list()
        max_order_theme_completed_user = await self._exam_repository.get_user_max_exam_order_value(user_id)
        max_order_allowed_user_number = max_order_theme_completed_user + 1
        user_theme_list = []

        for theme in theme_list:
            user_theme = UserTheme(
                theme=theme,
                is_enable=True if theme.theme_order <= max_order_allowed_user_number else False
            )
            user_theme_list.append(user_theme)

        return user_theme_list
