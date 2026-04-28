from dataclasses import dataclass
from typing import BinaryIO

from src.core.assistant.dto.file import CreateFileDTO


@dataclass(frozen=True)
class CreateThemeDTO:
    title: str
    file_list: list[CreateFileDTO]
