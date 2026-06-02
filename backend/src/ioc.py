from typing import AsyncGenerator

from aiobotocore.client import AioBaseClient
from aiobotocore.session import ClientCreatorContext, get_session
from botocore.client import Config as ClientConfig
from dishka import Provider, from_context, Scope, provide, make_async_container
from langchain_chroma import Chroma
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession

from src.config import Config, config
from src.core.assistant.interfaces.repositories.answer import AnswerRepository
from src.core.assistant.interfaces.repositories.exam import ExamRepository
from src.core.assistant.interfaces.repositories.exam_question import ExamQuestionRepository
from src.core.assistant.interfaces.repositories.exam_theme import ExamThemeRepository
from src.core.assistant.interfaces.repositories.question import QuestionRepository
from src.core.assistant.interfaces.repositories.stat import StatRepository
from src.core.assistant.interfaces.repositories.theme import ThemeRepository
from src.core.assistant.interfaces.uow.answer import AnswerUnitOfWork
from src.core.assistant.interfaces.uow.theme import ThemeUnitOfWork
from src.core.assistant.repositories.answer import SQLAlchemyAnswerRepository
from src.core.assistant.repositories.exam import SQLAlchemyExamRepository
from src.core.assistant.repositories.exam_question import SQLAlchemyExamQuestionRepository
from src.core.assistant.repositories.exam_theme import SQLAlchemyExamThemeRepository
from src.core.assistant.repositories.question import SQLAlchemyQuestionRepository
from src.core.assistant.repositories.stat import SQLAlchemyStatRepository
from src.core.assistant.repositories.theme import SQLAlchemyThemeRepository
from src.core.assistant.uow.answer import SQLAlchemyAnswerUnitOfWork
from src.core.assistant.uow.theme import SQLAlchemyThemeUnitOfWork
from src.core.assistant.use_cases.answer import CreateAnswerUseCase, GetUserAnswerListByExamIdUseCase, \
    GetAllUsersAnswerUseCase
from src.core.assistant.use_cases.exam import CreateExamUseCase, GetExamUseCase, GetUsersExamUseCase, \
    GetUserInWorkExamUseCase
from src.core.assistant.use_cases.exam_question import AskExamQuestionUseCase, GetExamQuestionListUseCase, \
    GetUserExamQuestionListUseCase, GetUnansweredUserExamQuestion
from src.core.assistant.use_cases.exam_theme import CreateExamThemeUseCase, GetExamThemeListUseCase, \
    GetExamThemeUseCase, GetUserExamListUseCase
from src.core.assistant.use_cases.question import CreateQuestionUseCase, GetQuestionUseCase, GetQuestionListUseCase, \
    CreateQuestionListUseCase
from src.core.assistant.use_cases.stat import GetStatByExamIdUseCase, GetAllUsersStatUseCase, GetUserStatForLastExam
from src.core.assistant.use_cases.theme import CreateThemeUseCase, GetThemeByIdUseCase, GetThemeListUseCase, \
    GetThemeFileUseCase, GetUserThemeUseCase
from src.core.commons.interfaces.storages.s3 import S3Storage
from src.core.commons.storages.s3 import MinioS3Storage
from src.core.commons.uow.base import UnitOfWork
from src.core.commons.uow.sql import SQLAlchemyUnitOfWork
from src.core.rag import DeepSeekFlashLLM, GigaChatEmbeddings, CHROMA_PATH


class SQLAlchemyProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_async_engine(self, _config: Config) -> AsyncEngine:
        return create_async_engine(_config.postgres.db_url, echo=False)

    @provide(scope=Scope.APP)
    def get_async_session_maker(
            self,
            engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(
            self,
            session_maker: async_sessionmaker[AsyncSession],
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session


class MinioProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    def get_client_creator(self) -> ClientCreatorContext:
        session = get_session()
        return session.create_client(
            "s3",
            endpoint_url=config.minio.s3_url,
            aws_access_key_id=config.minio.user,
            aws_secret_access_key=config.minio.password,
            region_name="us-east-1",
            config=ClientConfig(
                connect_timeout=50,
                read_timeout=70,
            )
        )

    @provide(scope=Scope.REQUEST)
    async def get_client(self, client_creator: ClientCreatorContext) -> AsyncGenerator[AioBaseClient, None]:
        async with client_creator as client:
            yield client

    @provide(scope=Scope.REQUEST)
    def get_s3_storage(self, client: AioBaseClient) -> S3Storage:
        return MinioS3Storage(
            bucket=config.minio.bucket,
            client=client,
        )


class SQLAlchemyUnitOfWorkProvider(Provider):
    scope = Scope.REQUEST

    sqlalchemy_uow = provide(SQLAlchemyUnitOfWork, provides=UnitOfWork)


class AssistantProvider(Provider):
    scope = Scope.REQUEST

    # LLM — синглтон на уровне приложения (DeepSeek V4 Flash)
    model = provide(DeepSeekFlashLLM, scope=Scope.APP)

    # Embeddings — синглтон на уровне приложения
    embeddings = provide(GigaChatEmbeddings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def provide_chroma_db(self, embeddings: GigaChatEmbeddings) -> Chroma:
        """Chroma DB — синглтон на уровне приложения.

        Инициализируется один раз при старте, а не на каждый запрос.
        Это избегает повторного открытия SQLite файла (66 МБ) на каждый ответ.
        """
        return Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    # repositories
    question_repository = provide(SQLAlchemyQuestionRepository, provides=QuestionRepository)
    exam_repository = provide(SQLAlchemyExamRepository, provides=ExamRepository)
    exam_question_repository = provide(SQLAlchemyExamQuestionRepository, provides=ExamQuestionRepository)
    answer_repository = provide(SQLAlchemyAnswerRepository, provides=AnswerRepository)
    stat_repository = provide(SQLAlchemyStatRepository, provides=StatRepository)
    theme_repository = provide(SQLAlchemyThemeRepository, provides=ThemeRepository)
    exam_theme_repository = provide(SQLAlchemyExamThemeRepository, provides=ExamThemeRepository)

    # uow
    answer_uow = provide(SQLAlchemyAnswerUnitOfWork, provides=AnswerUnitOfWork)
    theme_uow = provide(SQLAlchemyThemeUnitOfWork, provides=ThemeUnitOfWork)

    # question use cases
    create_question_use_case = provide(CreateQuestionUseCase)
    create_question_list_use_case = provide(CreateQuestionListUseCase)
    get_question_use_case = provide(GetQuestionUseCase)
    get_question_list_use_case = provide(GetQuestionListUseCase)

    # exam use case
    create_exam_use_case = provide(CreateExamUseCase)
    get_exam_use_case = provide(GetExamUseCase)
    get_users_exam_list_use_case = provide(GetUsersExamUseCase)
    get_user_exam_in_work_use_case = provide(GetUserInWorkExamUseCase)

    # exam question use case
    ask_exam_question_use_case = provide(AskExamQuestionUseCase)
    get_exam_question_list_use_case = provide(GetExamQuestionListUseCase)
    get_user_exam_question_list_use_case = provide(GetUserExamQuestionListUseCase)
    get_unanswered_question_use_case = provide(GetUnansweredUserExamQuestion)

    # answer use case
    create_answer_use_case = provide(CreateAnswerUseCase)
    get_user_answer_list_by_exam_id_use_case = provide(GetUserAnswerListByExamIdUseCase)
    get_all_users_answer_use_case = provide(GetAllUsersAnswerUseCase)

    # stat use case
    get_stat_by_exam_id_use_case = provide(GetStatByExamIdUseCase)
    get_all_users_stat_use_case = provide(GetAllUsersStatUseCase)
    get_user_stat_for_last_exam = provide(GetUserStatForLastExam)

    # theme use case
    create_theme_use_case = provide(CreateThemeUseCase)
    get_theme_by_id_use_case = provide(GetThemeByIdUseCase)
    get_theme_list_use_case = provide(GetThemeListUseCase)
    get_theme_file_use_case = provide(GetThemeFileUseCase)
    get_user_theme_list_use_case = provide(GetUserThemeUseCase)

    # exam theme use case
    create_exam_theme_use_case = provide(CreateExamThemeUseCase)
    get_exam_theme_list_use_case = provide(GetExamThemeListUseCase)
    get_exam_theme_use_case = provide(GetExamThemeUseCase)
    get_user_exam_theme_list_use_case = provide(GetUserExamListUseCase)


container = make_async_container(
    SQLAlchemyProvider(),
    MinioProvider(),
    SQLAlchemyUnitOfWorkProvider(),
    AssistantProvider(),
    context={Config: config, }
)
