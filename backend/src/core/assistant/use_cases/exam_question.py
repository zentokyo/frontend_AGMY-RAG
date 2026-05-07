import logging
import uuid
from datetime import datetime

from src.core.assistant.dto.exam_question import AskExamQuestionDTO
from src.core.assistant.entities.exam import ExamStatus, ExamRate
from src.core.assistant.entities.exam_question import ExamQuestion
from src.core.assistant.exceptions.exam import ExamNotFoundException, ExamWithoutQuestionException, \
    UserInWorkExamNotFoundException
from src.core.assistant.exceptions.exam_question import UserHaveUnansweredQuestionException, \
    ExamQuestionNotFoundException
from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_question import ExamQuestionRepository
from src.core.assistant.interfaces.repositories.question import QuestionRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository

logger = logging.getLogger(__name__)


class BaseExamQuestionUseCase:
    def __init__(self, exam_question_repository: ExamQuestionRepository):
        self._exam_question_repository = exam_question_repository


class AskExamQuestionUseCase(BaseExamQuestionUseCase):
    def __init__(
            self,
            exam_question_repository: ExamQuestionRepository,
            question_repository: QuestionRepository,
            exam_repository: ExamRepository,
            theme_repository: ThemeRepository,
            answer_repository: AnswerRepository,
    ):
        self._question_repository = question_repository
        self._exam_repository = exam_repository
        self._theme_repository = theme_repository
        self._answer_repository = answer_repository
        super().__init__(exam_question_repository)

    async def _complete_exam(self, exam, theme) -> None:
        """Завершить экзамен: выставить статус, оценку, время окончания."""
        exam.status = ExamStatus.COMPLETED
        exam.end_exam = datetime.now()
        if theme is not None:
            correct_answer_count = await self._answer_repository.get_correct_answers_count(exam.exam_id)
            max_theme_question_count = await self._question_repository.get_question_count(theme.theme_id)
            logger.info("Экзамен %s завершается: %d/%d правильных ответов",
                        exam.exam_id, correct_answer_count, max_theme_question_count)
            if correct_answer_count == max_theme_question_count:
                exam.rate = ExamRate.ALL_CORRECT
            else:
                exam.rate = ExamRate.BAD
        else:
            exam.rate = ExamRate.BAD
        await self._exam_repository.update_exam(exam, autocommit=True)

    async def __call__(self, ask_exam_question_dto: AskExamQuestionDTO) -> ExamQuestion:
        exam = await self._exam_repository.get_user_in_work_exam(ask_exam_question_dto.user_id)
        theme = await self._theme_repository.get_theme_by_title(exam.theme.title)

        if not (await self._exam_question_repository.check_all_exam_question_answered(exam.exam_id)):
            raise UserHaveUnansweredQuestionException(exam_id=exam.exam_id)

        exam_question_list = await self._exam_question_repository.get_exam_question_list(exam.exam_id)
        question_list = [exam_question.question for exam_question in exam_question_list]

        try:
            if theme is None:
                question = await self._question_repository.get_random_question(exclude=question_list)
            else:
                question = await self._question_repository.get_random_question_for_theme(theme=theme,
                                                                                         exclude=question_list)
        except ExamQuestionNotFoundException:
            # Вопросы закончились — завершаем экзамен
            logger.info("Вопросы закончились для экзамена %s, завершаем.", exam.exam_id)
            await self._complete_exam(exam, theme)
            # TODO: Использовать отдельное исключение ExamCompletedException вместо
            #  UserInWorkExamNotFoundException для корректной семантики.
            raise UserInWorkExamNotFoundException(ask_exam_question_dto.user_id)

        exam_question = ExamQuestion(
            exam_id=exam.exam_id,
            question=question,
        )

        await self._exam_question_repository.add_exam_question(exam_question)

        return exam_question


class GetExamQuestionListUseCase(BaseExamQuestionUseCase):
    def __init__(
            self,
            exam_question_repository: ExamQuestionRepository,
            exam_repository: ExamRepository
    ):
        self._exam_repository = exam_repository
        super().__init__(exam_question_repository)

    async def __call__(self, exam_id: uuid.UUID) -> list[ExamQuestion]:
        if not await self._exam_repository.check_exam_exists(exam_id):
            raise ExamNotFoundException(exam_id=exam_id)

        exam_question_list = await self._exam_question_repository.get_exam_question_list(exam_id)

        if not exam_question_list:
            raise ExamWithoutQuestionException(exam_id)

        return exam_question_list


class GetUserExamQuestionListUseCase(BaseExamQuestionUseCase):
    def __init__(
            self,
            exam_question_repository: ExamQuestionRepository,
            exam_repository: ExamRepository
    ):
        self._exam_repository = exam_repository
        super().__init__(exam_question_repository)

    async def __call__(self, user_id: int) -> list[ExamQuestion]:
        exam = await self._exam_repository.get_user_in_work_exam(user_id)

        return await self._exam_question_repository.get_exam_question_list(exam.exam_id)


class GetUnansweredUserExamQuestion(BaseExamQuestionUseCase):
    def __init__(
            self,
            exam_question_repository: ExamQuestionRepository,
            exam_repository: ExamRepository
    ):
        self._exam_repository = exam_repository
        super().__init__(exam_question_repository)

    async def __call__(self, user_id: int) -> ExamQuestion:
        exam = await self._exam_repository.get_user_in_work_exam(user_id)

        return await self._exam_question_repository.get_unanswered_exam_question(exam.exam_id)
