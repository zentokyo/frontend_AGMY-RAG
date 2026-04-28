import uuid
from dataclasses import dataclass, field

from src.core.assistant.entities.file import File


@dataclass
class Theme:
    theme_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    title: str
    file_list: list[File] = field(default_factory=list, kw_only=True)
    theme_order: int


@dataclass
class UserTheme:
    theme: Theme
    is_enable: bool


@dataclass
class ThemeFile:
    file_id: uuid.UUID
    theme_id: uuid.UUID
