import uuid
from typing import Self

from pydantic import BaseModel

from src.core.assistant.entities.theme import Theme, UserTheme


class ThemeResponseSchema(BaseModel):
    theme_id: uuid.UUID
    title: str
    file_list: list[str]

    @classmethod
    def from_entity(cls, theme: Theme) -> Self:
        return cls(
            theme_id=theme.theme_id,
            title=theme.title,
            file_list=[file.filename for file in theme.file_list]
        )


class ThemeShortResponse(BaseModel):
    theme_id: uuid.UUID
    title: str

    @classmethod
    def from_entity(cls, theme: Theme) -> Self:
        return cls(
            theme_id=theme.theme_id,
            title=theme.title,
        )


class UserThemeResponseSchema(ThemeResponseSchema):
    is_enable: bool

    @classmethod
    def from_entity(cls, user_theme: UserTheme) -> Self:
        return cls(
            theme_id=user_theme.theme.theme_id,
            title=user_theme.theme.title,
            file_list=[file.filename for file in user_theme.theme.file_list],
            is_enable=user_theme.is_enable,
        )
