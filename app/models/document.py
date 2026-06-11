import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="processing")  # processing | ready | error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.original_filename,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "total_chunks": self.total_chunks,
            "total_pages": self.total_pages,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
        }
