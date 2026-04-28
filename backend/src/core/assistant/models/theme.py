import uuid
from typing import Self

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.theme import Theme, ThemeFile
from src.core.assistant.models.file import FileSQLModel
from src.core.commons.model import SQLBaseModel


class ThemeFileSQLModel(SQLBaseModel):
    __tablename__ = "theme_file"

    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("theme.theme_id"), primary_key=True)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(FileSQLModel.file_id), primary_key=True)

    @classmethod
    def from_entity(cls, theme_file: ThemeFile) -> Self:
        return cls(
            theme_id=theme_file.theme_id,
            file_id=theme_file.file_id,
        )


class ThemeSQLModel(SQLBaseModel):
    __tablename__ = "theme"

    theme_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    title: Mapped[str]
    theme_order: Mapped[int]

    file_list: Mapped[list[FileSQLModel]] = relationship(
        secondary="theme_file",
        back_populates="theme_list",
    )

    @classmethod
    def from_entity(cls, theme: Theme) -> Self:
        return cls(
            theme_id=theme.theme_id,
            title=theme.title,
            theme_order=theme.theme_order,
        )

    def to_entity(self) -> Theme:
        return Theme(
            theme_id=self.theme_id,
            title=self.title,
            file_list=[file.to_entity() for file in self.file_list],
            theme_order=self.theme_order,
        )
