import uuid
from dataclasses import dataclass, field


@dataclass
class File:
    file_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    filename: str
