import logging
import uuid

from src.core.assistant.dto.exam import CreateExamDTO
from src.core.assistant.entities.exam import Exam, ExamType
from src.core.assistant.exceptions.exam import UserAlreadyTakingExamException, ExamQuestionCountException
from src.core.assistant.exceptions.exam_theme import ExamThemeNotFoundException, ExamThemeNotAllowedException
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository

logger = logging.getLogger(__name__)

# Названия тем, которые считаются итоговыми экзаменами.
# TODO: Заменить на поле is_final в ExamTheme entity + миграция БД.
_FINAL_EXAM_TITLES = frozenset({"Итоговый экзамен"})


class BaseExamUseCase:
    def __init__(self, exam_repository: ExamRepository):
        self._exam_repository = exam_repository


class CreateExamUseCase(BaseExamUseCase):
    def __init__(
            self,
            exam_repository: ExamRepository,
            exam_theme_repository: ExamThemeRepository,
    ):
        super().__init__(exam_repository)
        self._exam_theme_repository = exam_theme_repository

    async def __call__(self, create_exam_dto: CreateExamDTO) -> Exam:
        if await self._exam_repository.check_user_exam_in_work(create_exam_dto.user_id):
            raise UserAlreadyTakingExamException(create_exam_dto.user_id)

        if not (0 < create_exam_dto.question_count <= 10):
            raise ExamQuestionCountException(create_exam_dto.question_count)

        try:
            exam_theme = await self._exam_theme_repository.get_exam_theme_by_id(create_exam_dto.exam_theme_id)
        except ExamThemeNotFoundException:
            exam_theme = await self._exam_theme_repository.get_exam_theme_by_theme_id(create_exam_dto.exam_theme_id)

        max_user_order = await self._exam_repository.get_user_max_exam_order_value(create_exam_dto.user_id)
        allowed_user_order = max_user_order + 1

        if exam_theme.exam_theme_order > allowed_user_order:
            raise ExamThemeNotAllowedException

        # TODO: Заменить на exam_theme.is_final после миграции БД
        exam_type = ExamType.FINAL if exam_theme.title in _FINAL_EXAM_TITLES else ExamType.NOT_FINAL

        exam = Exam(
            create_exam_dto.user_id,
            question_count=create_exam_dto.question_count,
            theme=exam_theme,
            type=exam_type,
        )

        await self._exam_repository.add_exam(exam)

        logger.info("Создан экзамен %s для user_id=%d, тема='%s', тип=%s",
                     exam.exam_id, create_exam_dto.user_id, exam_theme.title, exam_type.value)

        return exam


class GetExamUseCase(BaseExamUseCase):
    async def __call__(self, exam_id: uuid.UUID) -> Exam:
        return await self._exam_repository.get_exam_by_id(exam_id)


class GetUsersExamUseCase(BaseExamUseCase):
    async def __call__(self, user_id: int) -> list[Exam]:
        return await self._exam_repository.get_user_exam_list(user_id)


class GetUserInWorkExamUseCase(BaseExamUseCase):
    async def __call__(self, user_id: int) -> Exam:
        return await self._exam_repository.get_user_in_work_exam(user_id)
