import uuid
from datetime import datetime
from typing import Self

from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.assistant.entities.file import File
from src.core.commons.model import SQLBaseModel


class FileSQLModel(SQLBaseModel):
    __tablename__ = "file"

    file_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    filename: Mapped[str]
    content_type: Mapped[str] = mapped_column(default="application/octet-stream")
    ingest_status: Mapped[str] = mapped_column(default="uploaded")
    ingest_error: Mapped[str | None]
    indexed_chunks: Mapped[int] = mapped_column(default=0)
    indexed_at: Mapped[datetime | None]
    created_at: Mapped[datetime | None]

    theme_list: Mapped[list["ThemeSQLModel"]] = relationship(
        secondary="theme_file",
        back_populates="file_list",
    )

    @classmethod
    def from_entity(cls, file: File) -> Self:
        return cls(
            file_id=file.file_id,
            filename=file.filename,
            content_type=file.content_type,
            ingest_status=file.ingest_status,
            ingest_error=file.ingest_error,
            indexed_chunks=file.indexed_chunks,
            indexed_at=file.indexed_at,
            created_at=file.created_at,
        )

    def to_entity(self) -> File:
        return File(
            file_id=self.file_id,
            filename=self.filename,
            content_type=self.content_type,
            ingest_status=self.ingest_status,
            ingest_error=self.ingest_error,
            indexed_chunks=self.indexed_chunks,
            indexed_at=self.indexed_at,
            created_at=self.created_at,
        )
