import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    doc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "doc_id": self.doc_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
