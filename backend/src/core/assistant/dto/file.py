from dataclasses import dataclass
from typing import BinaryIO


@dataclass(frozen=True)
class CreateFileDTO:
    filename: str
    file_data: BinaryIO
