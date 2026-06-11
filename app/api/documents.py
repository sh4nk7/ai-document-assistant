import os
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.db.crud import create_document, get_document, list_documents, update_document, delete_document
from app.core.ingestion import ingest_pdf, delete_doc_vectors
from app.utils.file_utils import validate_upload, safe_filename

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", status_code=201, summary="Carica un file PDF e lo indicizza")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Carica un PDF, lo suddivide in chunk, genera gli embedding e li salva in Qdrant.
    I metadati del documento vengono salvati in PostgreSQL.
    """
    pdf_bytes = await validate_upload(file)
    fname = safe_filename(file.filename or "document.pdf")

    doc = await create_document(
        db,
        filename=fname,
        original_filename=file.filename or "document.pdf",
        file_size_bytes=len(pdf_bytes),
        status="processing",
    )

    # Save file to disk
    file_path = os.path.join(settings.UPLOAD_DIR, fname)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    try:
        total_chunks, total_pages = await ingest_pdf(pdf_bytes, doc.id)
        await update_document(db, doc.id, total_chunks=total_chunks, total_pages=total_pages, status="ready")
        doc = await get_document(db, doc.id)
    except Exception as exc:
        logger.exception("Ingestion failed for doc_id=%s", doc.id)
        await update_document(db, doc.id, status="error")
        raise HTTPException(status_code=500, detail=f"Errore durante l'indicizzazione: {exc}") from exc

    return doc.to_dict()


@router.get("/", summary="Elenca tutti i documenti caricati")
async def list_docs(db: AsyncSession = Depends(get_db)):
    docs = await list_documents(db)
    return [d.to_dict() for d in docs]


@router.get("/{doc_id}", summary="Dettaglio di un documento")
async def get_doc(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    return doc.to_dict()


@router.delete("/{doc_id}", status_code=204, summary="Elimina documento e i suoi vettori")
async def delete_doc(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento non trovato.")

    # Remove from Qdrant
    await delete_doc_vectors(doc_id)

    # Remove file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    await delete_document(db, doc_id)
