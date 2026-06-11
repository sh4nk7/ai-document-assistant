"""RAG retrieval pipeline implemented with LangGraph.

Graph nodes:
  embed_query → search_qdrant → build_prompt → call_llm → done
"""

import logging
from typing import TypedDict, AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, VectorParams, Distance

from app.config import settings
from app.core.llm import get_embeddings, get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sei un assistente esperto nell'analisi di documenti.
Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE sul contesto fornito.
Se la risposta non è contenuta nel contesto, rispondi: "Non ho trovato informazioni sufficienti nel documento per rispondere."
Cita il numero di pagina quando possibile."""


# ── LangGraph state ──────────────────────────────────────────────────────────

class RAGState(TypedDict):
    question: str
    doc_id: str | None
    top_k: int
    query_vector: list[float] | None
    retrieved_chunks: list[dict]
    prompt_messages: list
    answer: str


# ── Graph nodes ──────────────────────────────────────────────────────────────

async def node_embed_query(state: RAGState) -> RAGState:
    embedder = get_embeddings()
    vector = await embedder.aembed_query(state["question"])
    return {**state, "query_vector": vector}


async def node_search_qdrant(state: RAGState) -> RAGState:
    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    search_filter = None
    if state.get("doc_id"):
        search_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=state["doc_id"]))]
        )

    results = await client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=state["query_vector"],
        limit=state["top_k"],
        query_filter=search_filter,
        with_payload=True,
    )
    await client.close()

    chunks = [
        {
            "text": r.payload.get("text", ""),
            "page_num": r.payload.get("page_num", 0),
            "chunk_index": r.payload.get("chunk_index", 0),
            "doc_id": r.payload.get("doc_id", ""),
            "score": r.score,
        }
        for r in results
    ]
    return {**state, "retrieved_chunks": chunks}


async def node_build_prompt(state: RAGState) -> RAGState:
    context_parts = []
    for i, chunk in enumerate(state["retrieved_chunks"], 1):
        context_parts.append(f"[Fonte {i} – Pagina {chunk['page_num']}]\n{chunk['text']}")
    context = "\n\n".join(context_parts) if context_parts else "Nessun contesto disponibile."

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Contesto:\n{context}\n\nDomanda: {state['question']}"),
    ]
    return {**state, "prompt_messages": messages}


async def node_call_llm(state: RAGState) -> RAGState:
    llm = get_llm()
    response = await llm.ainvoke(state["prompt_messages"])
    return {**state, "answer": response.content}


# ── Build the graph ──────────────────────────────────────────────────────────

def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)
    graph.add_node("embed_query", node_embed_query)
    graph.add_node("search_qdrant", node_search_qdrant)
    graph.add_node("build_prompt", node_build_prompt)
    graph.add_node("call_llm", node_call_llm)

    graph.set_entry_point("embed_query")
    graph.add_edge("embed_query", "search_qdrant")
    graph.add_edge("search_qdrant", "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile()


_rag_graph = None


def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = build_rag_graph()
    return _rag_graph


# ── Public helpers ───────────────────────────────────────────────────────────

async def run_rag(question: str, doc_id: str | None = None, top_k: int | None = None) -> dict:
    graph = get_rag_graph()
    initial_state: RAGState = {
        "question": question,
        "doc_id": doc_id,
        "top_k": top_k or settings.TOP_K,
        "query_vector": None,
        "retrieved_chunks": [],
        "prompt_messages": [],
        "answer": "",
    }
    final_state = await graph.ainvoke(initial_state)
    return {
        "answer": final_state["answer"],
        "sources": final_state["retrieved_chunks"],
    }


async def semantic_search(query: str, doc_id: str | None = None, top_k: int = 5) -> list[dict]:
    embedder = get_embeddings()
    vector = await embedder.aembed_query(query)

    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    search_filter = None
    if doc_id:
        search_filter = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )

    results = await client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )
    await client.close()

    return [
        {
            "text": r.payload.get("text", ""),
            "page_num": r.payload.get("page_num", 0),
            "doc_id": r.payload.get("doc_id", ""),
            "chunk_index": r.payload.get("chunk_index", 0),
            "score": round(r.score, 4),
        }
        for r in results
    ]


async def ensure_collection() -> None:
    client = AsyncQdrantClient(url=settings.QDRANT_URL)
    existing = await client.get_collections()
    names = [c.name for c in existing.collections]
    if settings.QDRANT_COLLECTION not in names:
        await client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=settings.QDRANT_VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s'", settings.QDRANT_COLLECTION)
    await client.close()
