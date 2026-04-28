import uuid

from src.core.assistant.entities.exam import ExamType
from src.core.assistant.entities.stat import Stat, StatWithAnswerList, TotalStat
from src.core.assistant.exceptions.exam import ExamNotCompletedException, UserHaveNotCompletedExamsException
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.stat import StatRepository


class BaseStatUseCase:
    def __init__(self, stat_repository: StatRepository):
        self._stat_repository = stat_repository


class GetStatByExamIdUseCase(BaseStatUseCase):
    def __init__(
            self,
            stat_repository: StatRepository,
            exam_repository: ExamRepository,
    ):
        super().__init__(stat_repository)
        self._exam_repository = exam_repository

    async def __call__(self, exam_id: uuid.UUID) -> Stat:
        if not await self._exam_repository.check_exam_completed(exam_id):
            raise ExamNotCompletedException(exam_id)

        return await self._stat_repository.get_stat_by_exam_id(exam_id)


class GetAllUsersStatUseCase(BaseStatUseCase):
    def __init__(
            self,
            stat_repository: StatRepository,
            exam_repository: ExamRepository,
    ):
        super().__init__(stat_repository)
        self._exam_repository = exam_repository

    async def __call__(self, user_id: int) -> TotalStat:
        if not await self._exam_repository.check_user_have_completed_exams(user_id):
            raise UserHaveNotCompletedExamsException(user_id)

        total_user_stat = await self._stat_repository.get_all_user_stat(user_id)
        stat_by_theme_list = await self._stat_repository.get_all_user_stat_by_theme(user_id)

        return TotalStat(
            total_answers=total_user_stat.total_answers,
            correct_answers=total_user_stat.correct_answers,
            stat_by_theme=stat_by_theme_list,
        )


class GetUserStatForLastExam(BaseStatUseCase):
    def __init__(
            self,
            stat_repository: StatRepository,
            exam_repository: ExamRepository,
    ):
        super().__init__(stat_repository)
        self._exam_repository = exam_repository

    async def __call__(self, user_id: int) -> StatWithAnswerList:
        exam = await self._exam_repository.get_last_user_completed_exam(user_id)
        if exam.type == ExamType.FINAL:
            return await self._stat_repository.get_exam_stat_w_answer_list(exam.exam_id)
        return await self._stat_repository.get_exam_stat_w_answer_and_model_list(exam.exam_id)
