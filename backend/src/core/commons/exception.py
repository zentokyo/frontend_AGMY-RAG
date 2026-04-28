from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class BaseAppException(Exception):
    @property
    def message(self) -> str:
        return "Базовая ошибка приложения!"


@dataclass(frozen=True, eq=False)
class S3StorageException(BaseAppException):
    @property
    def message(self) -> str:
        return "Файловое хранилище недоступно!"


@dataclass(frozen=True, eq=False)
class S3FileNotFoundException(S3StorageException):
    filename: str

    @property
    def message(self) -> str:
        return f"Файл не найден в хранилище {self.filename}"


@dataclass(frozen=True, eq=False)
class NotGivenException(BaseAppException):
    field_name: str

    @property
    def message(self) -> str:
        return f"Поле {self.field_name} не загружено!"
