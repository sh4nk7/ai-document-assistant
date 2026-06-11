import uuid
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.crud import get_document, save_message, get_conversation
from app.core.retrieval import run_rag
from app.core.llm import get_llm
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    doc_id: str | None = None
    session_id: str | None = None
    top_k: int = Field(default=4, ge=1, le=20)
    stream: bool = False


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[dict]


@router.post("/", response_model=ChatResponse, summary="Fai una domanda sui documenti (RAG)")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Riceve una domanda, recupera i chunk rilevanti da Qdrant e genera una risposta
    con il modello LLM configurato. Se `doc_id` è fornito, filtra su quel documento.
    Se `stream=true` restituisce Server-Sent Events.
    """
    # Validate doc_id if provided
    if request.doc_id:
        doc = await get_document(db, request.doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Documento non trovato.")
        if doc.status != "ready":
            raise HTTPException(status_code=409, detail="Il documento non è ancora pronto.")

    session_id = request.session_id or str(uuid.uuid4())

    if request.stream:
        return StreamingResponse(
            _stream_rag(request.question, request.doc_id, request.top_k, session_id, db),
            media_type="text/event-stream",
        )

    result = await run_rag(request.question, request.doc_id, request.top_k)

    # Persist conversation
    await save_message(db, session_id, "user", request.question, request.doc_id)
    await save_message(db, session_id, "assistant", result["answer"], request.doc_id)

    return ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        sources=result["sources"],
    )


async def _stream_rag(
    question: str,
    doc_id: str | None,
    top_k: int,
    session_id: str,
    db: AsyncSession,
) -> AsyncIterator[str]:
    from app.core.retrieval import node_embed_query, node_search_qdrant, node_build_prompt, RAGState

    state: RAGState = {
        "question": question,
        "doc_id": doc_id,
        "top_k": top_k,
        "query_vector": None,
        "retrieved_chunks": [],
        "prompt_messages": [],
        "answer": "",
    }
    state = await node_embed_query(state)
    state = await node_search_qdrant(state)
    state = await node_build_prompt(state)

    llm = get_llm()
    full_answer = []

    async for chunk in llm.astream(state["prompt_messages"]):
        token = chunk.content
        full_answer.append(token)
        yield f"data: {token}\n\n"

    # Persist after streaming completes
    answer_text = "".join(full_answer)
    await save_message(db, session_id, "user", question, doc_id)
    await save_message(db, session_id, "assistant", answer_text, doc_id)
    yield "data: [DONE]\n\n"


@router.get("/history/{session_id}", summary="Cronologia di una sessione di chat")
async def chat_history(session_id: str, db: AsyncSession = Depends(get_db)):
    messages = await get_conversation(db, session_id)
    return [m.to_dict() for m in messages]
