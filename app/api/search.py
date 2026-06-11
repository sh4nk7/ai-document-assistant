from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.session import get_db
from app.db.crud import get_document
from app.core.retrieval import semantic_search

router = APIRouter()


@router.get("/", summary="Ricerca semantica nei documenti indicizzati")
async def search(
    q: str = Query(..., min_length=1, max_length=1000, description="Testo da cercare"),
    top_k: int = Query(default=5, ge=1, le=20, description="Numero di risultati"),
    doc_id: str | None = Query(default=None, description="Filtra su un singolo documento"),
    db: AsyncSession = Depends(get_db),
):
    """
    Esegue una ricerca semantica full-collection o su un documento specifico.
    Restituisce i chunk più simili con punteggio di similarità coseno.
    """
    if doc_id:
        doc = await get_document(db, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Documento non trovato.")

    results = await semantic_search(q, doc_id=doc_id, top_k=top_k)
    return {
        "query": q,
        "doc_id": doc_id,
        "total": len(results),
        "results": results,
    }
