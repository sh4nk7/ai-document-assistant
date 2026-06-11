from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.document import Document
from app.models.conversation import Conversation


# ── Document CRUD ────────────────────────────────────────────────────────────

async def create_document(db: AsyncSession, **kwargs) -> Document:
    doc = Document(**kwargs)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, doc_id: str) -> Document | None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def list_documents(db: AsyncSession) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.upload_date.desc()))
    return list(result.scalars().all())


async def update_document(db: AsyncSession, doc_id: str, **kwargs) -> Document | None:
    doc = await get_document(db, doc_id)
    if doc is None:
        return None
    for key, value in kwargs.items():
        setattr(doc, key, value)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    result = await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()
    return result.rowcount > 0


# ── Conversation CRUD ────────────────────────────────────────────────────────

async def save_message(db: AsyncSession, session_id: str, role: str, content: str, doc_id: str | None = None) -> Conversation:
    msg = Conversation(session_id=session_id, role=role, content=content, doc_id=doc_id)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation(db: AsyncSession, session_id: str) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.created_at)
    )
    return list(result.scalars().all())
