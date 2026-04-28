import uuid
from typing import Self

from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.file import File
from src.core.commons.model import SQLBaseModel


class FileSQLModel(SQLBaseModel):
    __tablename__ = "file"

    file_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    filename: Mapped[str]

    theme_list: Mapped[list["ThemeSQLModel"]] = relationship(
        secondary="theme_file",
        back_populates="file_list",
    )

    @classmethod
    def from_entity(cls, file: File) -> Self:
        return cls(
            file_id=file.file_id,
            filename=file.filename,
        )

    def to_entity(self) -> File:
        return File(
            file_id=self.file_id,
            filename=self.filename,
        )
