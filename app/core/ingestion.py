"""PDF ingestion pipeline: parse → chunk → embed → store in Qdrant."""

import io
import logging
from dataclasses import dataclass

from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.config import settings
from app.core.llm import get_embeddings

logger = logging.getLogger(__name__)


@dataclass
class ChunkRecord:
    doc_id: str
    chunk_index: int
    page_num: int
    text: str


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[list[tuple[int, str]], int]:
    """Return list of (page_num, page_text) and total page count."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append((i + 1, text))
    return pages, len(reader.pages)


def split_into_chunks(pages: list[tuple[int, str]], doc_id: str) -> list[ChunkRecord]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    records: list[ChunkRecord] = []
    chunk_index = 0
    for page_num, page_text in pages:
        if not page_text.strip():
            continue
        chunks = splitter.split_text(page_text)
        for chunk in chunks:
            if chunk.strip():
                records.append(ChunkRecord(
                    doc_id=doc_id,
                    chunk_index=chunk_index,
                    page_num=page_num,
                    text=chunk.strip(),
                ))
                chunk_index += 1
    return records


async def embed_and_store(records: list[ChunkRecord]) -> None:
    if not records:
        return

    embedder = get_embeddings()
    client = AsyncQdrantClient(url=settings.QDRANT_URL)

    texts = [r.text for r in records]
    vectors = await embedder.aembed_documents(texts)

    points = [
        PointStruct(
            id=f"{r.doc_id}_{r.chunk_index}",
            vector=vectors[i],
            payload={
                "doc_id": r.doc_id,
                "chunk_index": r.chunk_index,
                "page_num": r.page_num,
                "text": r.text,
            },
        )
        for i, r in enumerate(records)
    ]

    await client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    await client.close()
    logger.info("Stored %d chunks for doc_id=%s", len(records), records[0].doc_id)


async def ingest_pdf(pdf_bytes: bytes, doc_id: str) -> tuple[int, int]:
    """Full ingestion pipeline. Returns (total_chunks, total_pages)."""
    pages, total_pages = extract_text_from_pdf(pdf_bytes)
    chunks = split_into_chunks(pages, doc_id)
    await embed_and_store(chunks)
    return len(chunks), total_pages


async def delete_doc_vectors(doc_id: str) -> None:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    await client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
    await client.close()
    logger.info("Deleted vectors for doc_id=%s", doc_id)
