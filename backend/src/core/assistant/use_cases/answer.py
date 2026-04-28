import asyncio
import uuid
from datetime import datetime

from src.core.assistant.dto.answer import CreateAnswerDTO
from src.core.assistant.entities.answer import Answer
from src.core.assistant.entities.exam import ExamStatus, ExamRate
from src.core.assistant.entities.exam_question import ExamQuestionStatus
from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.uow.answer import AnswerUnitOfWork
from src.core.rag import GigaChatLiteLLM, answer_question


class CreateAnswerUseCase:
    def __init__(
            self,
            uow: AnswerUnitOfWork,
            model: GigaChatLiteLLM,
    ):
        self._uow = uow
        self._llm = model

    async def __call__(self, create_answer_dto: CreateAnswerDTO) -> Answer:
        async with self._uow:
            exam = await self._uow.exam_repository.get_user_in_work_exam(create_answer_dto.user_id)

            exam_question = await self._uow.exam_question_repository.get_unanswered_exam_question(exam.exam_id)
            exam_question.status = ExamQuestionStatus.ANSWERED
            await self._uow.exam_question_repository.update_exam_question(exam_question)

            current_answered_question_count = await self._uow.exam_question_repository.get_answered_exam_question_count(
                exam.exam_id
            )

            is_correct_answer = await asyncio.to_thread(
                answer_question,
                exam_question.question.text,
                create_answer_dto.answer_text,
                self._llm,
            )

            print(is_correct_answer)

            answer = Answer(
                exam_question=exam_question,
                answer_text=create_answer_dto.answer_text,
                is_correct=is_correct_answer if is_correct_answer else False,
            )

            await self._uow.answer_repository.add_answer(answer)

            if exam.question_count - current_answered_question_count == 0:
                exam.status = ExamStatus.COMPLETED
                exam.end_exam = datetime.now()
                correct_answer_count = await self._uow.answer_repository.get_correct_answers_count(exam.exam_id)
                if correct_answer_count == exam.question_count:
                    exam.rate = ExamRate.ALL_CORRECT
                else:
                    exam.rate = ExamRate.BAD
                await self._uow.exam_repository.update_exam(exam)

            await self._uow.commit()

            return answer


class GetUserAnswerListByExamIdUseCase:
    def __init__(
            self,
            exam_repository: ExamRepository,
            answer_repository: AnswerRepository,
    ):
        self._exam_repository = exam_repository
        self._answer_repository = answer_repository

    async def __call__(self, exam_id: uuid.UUID) -> list[Answer]:
        exam = await self._exam_repository.get_exam_by_id(exam_id)

        return await self._answer_repository.get_answer_list_by_exam_id(exam.exam_id)


class GetAllUsersAnswerUseCase:
    def __init__(
            self,
            answer_repository: AnswerRepository,
    ):
        self._answer_repository = answer_repository

    async def __call__(self, user_id: int) -> list[Answer]:
        return await self._answer_repository.get_answer_list_by_user_id(user_id)
