import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class File:
    file_id: uuid.UUID = field(default_factory=uuid.uuid4, kw_only=True)
    filename: str
    content_type: str = "application/octet-stream"
    ingest_status: str = "uploaded"
    ingest_error: str | None = None
    indexed_chunks: int = 0
    indexed_at: datetime | None = None
    created_at: datetime | None = None
